import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from ml_engine import ml_engine
from chatbot import process_chat_message

# Path configuration
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BACKEND_DIR, "curriculum_tracker.db")
FRONTEND_DIR = os.path.abspath(os.path.join(BACKEND_DIR, "..", "frontend"))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')

# Target coordinate for GPS validation (e.g. classroom location)
TARGET_LAT = 12.9716
TARGET_LNG = 77.5946
GPS_TOLERANCE_METERS = 150.0  # Approx tolerance (roughly 0.0013 degrees latitude/longitude)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Helper to execute queries
def db_query(query, args=(), one=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, args)
    rv = cursor.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def db_commit(query, args=()):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, args)
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

# --- FRONTEND ROUTING ---

@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    # Fallback to serving from the static folder if file exists
    if os.path.exists(os.path.join(FRONTEND_DIR, path)):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')

# --- API ENDPOINTS ---

# 1. AUTHENTICATION
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Missing credentials'}), 400
        
    user = db_query("SELECT id, username, name, role, email FROM users WHERE username = ? AND password = ?", 
                    (username, password), one=True)
                    
    if user:
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'name': user['name'],
                'role': user['role'],
                'email': user['email']
            }
        })
    else:
        return jsonify({'success': False, 'error': 'Invalid username or password'}), 401

# 2. DASHBOARD ANALYTICS
@app.route('/api/dashboard/stats', methods=['GET'])
def get_stats():
    role = request.args.get('role')
    user_id = request.args.get('user_id')
    
    if not role:
        return jsonify({'error': 'Role parameter is required'}), 400
        
    if role == 'student':
        if not user_id:
            return jsonify({'error': 'Student user_id is required'}), 400
            
        # Overall attendance rate
        att_rows = db_query("SELECT status FROM attendance WHERE student_id = ?", (user_id,))
        total_att = len(att_rows)
        present_att = sum(1 for r in att_rows if r['status'] == 'present')
        attendance_pct = (present_att / total_att * 100.0) if total_att > 0 else 100.0
        
        # Pending assignments
        pending_rows = db_query('''
            SELECT COUNT(*) as count 
            FROM assignments a
            LEFT JOIN submissions s ON a.id = s.assignment_id AND s.student_id = ?
            WHERE s.id IS NULL
        ''', (user_id,), one=True)
        pending_assignments = pending_rows['count']
        
        # Average grade on graded assignments
        grade_rows = db_query("SELECT marks, max_marks FROM submissions WHERE student_id = ? AND marks IS NOT NULL", (user_id,))
        grades = [(g['marks'] / g['max_marks'] * 100.0) for g in grade_rows if g['max_marks'] > 0]
        avg_grade = sum(grades) / len(grades) if grades else 0.0
        
        # Registered activities
        act_rows = db_query("SELECT COUNT(*) as count FROM activity_registrations WHERE student_id = ?", (user_id,), one=True)
        registered_activities = act_rows['count']
        
        # Subject-wise attendance and syllabus completion
        subjects = db_query("SELECT id, name, code FROM subjects")
        subject_data = []
        for sub in subjects:
            # Subject attendance
            sub_att = db_query("SELECT status FROM attendance WHERE student_id = ? AND subject_id = ?", (user_id, sub['id']))
            sub_total = len(sub_att)
            sub_present = sum(1 for r in sub_att if r['status'] == 'present')
            sub_att_pct = (sub_present / sub_total * 100.0) if sub_total > 0 else 100.0
            
            # Subject curriculum completion
            total_topics = db_query("SELECT COUNT(*) as count FROM curriculum_topics WHERE subject_id = ?", (sub['id'],), one=True)['count']
            completed_topics = db_query("SELECT COUNT(*) as count FROM curriculum_topics WHERE subject_id = ? AND status = 'completed'", (sub['id'],), one=True)['count']
            sub_comp_pct = (completed_topics / total_topics * 100.0) if total_topics > 0 else 0.0
            
            subject_data.append({
                'id': sub['id'],
                'name': sub['name'],
                'code': sub['code'],
                'attendance_pct': round(sub_att_pct, 1),
                'curriculum_pct': round(sub_comp_pct, 1)
            })
            
        return jsonify({
            'attendance_pct': round(attendance_pct, 1),
            'pending_assignments': pending_assignments,
            'avg_grade': round(avg_grade, 1),
            'registered_activities': registered_activities,
            'subjects': subject_data
        })
        
    elif role == 'faculty':
        if not user_id:
            return jsonify({'error': 'Faculty user_id is required'}), 400
            
        # Get subjects taught by this faculty
        faculty_subjects = db_query("SELECT id, name, code FROM subjects WHERE faculty_id = ?", (user_id,))
        sub_ids = [s['id'] for s in faculty_subjects]
        
        if not sub_ids:
            return jsonify({
                'avg_attendance_pct': 0.0,
                'ungraded_submissions': 0,
                'curriculum_pct': 0.0,
                'subjects': [],
                'at_risk_students': []
            })
            
        # 1. Average attendance rate across their subjects
        placeholders = ','.join('?' for _ in sub_ids)
        att_rows = db_query(f"SELECT status FROM attendance WHERE subject_id IN ({placeholders})", sub_ids)
        total_att = len(att_rows)
        present_att = sum(1 for r in att_rows if r['status'] == 'present')
        avg_attendance = (present_att / total_att * 100.0) if total_att > 0 else 100.0
        
        # 2. Ungraded submissions for their subjects
        ungraded_rows = db_query(f'''
            SELECT COUNT(*) as count 
            FROM submissions s
            JOIN assignments a ON s.assignment_id = a.id
            WHERE a.subject_id IN ({placeholders}) AND s.marks IS NULL
        ''', sub_ids, one=True)
        ungraded_submissions = ungraded_rows['count']
        
        # 3. Average curriculum progress
        total_topics = db_query(f"SELECT COUNT(*) as count FROM curriculum_topics WHERE subject_id IN ({placeholders})", sub_ids, one=True)['count']
        completed_topics = db_query(f"SELECT COUNT(*) as count FROM curriculum_topics WHERE subject_id IN ({placeholders}) AND status = 'completed'", sub_ids, one=True)['count']
        curriculum_pct = (completed_topics / total_topics * 100.0) if total_topics > 0 else 0.0
        
        # 4. At-risk students (using ML predictions for all students)
        students = db_query("SELECT id, name, email FROM users WHERE role = 'student'")
        at_risk_students = []
        for s in students:
            pred = ml_engine.predict_student_status(s['id'])
            if pred['attendance_risk'] == 'At Risk':
                at_risk_students.append({
                    'id': s['id'],
                    'name': s['name'],
                    'email': s['email'],
                    'attendance_rate': round(pred['features']['attendance_rate'], 1),
                    'predicted_grade': pred['predicted_final_score'],
                    'insight': pred['insight']
                })
                
        subjects_list = []
        for s in faculty_subjects:
            subjects_list.append({
                'id': s['id'],
                'name': s['name'],
                'code': s['code']
            })
            
        return jsonify({
            'avg_attendance_pct': round(avg_attendance, 1),
            'ungraded_submissions': ungraded_submissions,
            'curriculum_pct': round(curriculum_pct, 1),
            'subjects': subjects_list,
            'at_risk_students': at_risk_students
        })
        
    elif role == 'admin':
        # Admin stats (global system dashboard)
        total_students = db_query("SELECT COUNT(*) as count FROM users WHERE role = 'student'", one=True)['count']
        total_faculty = db_query("SELECT COUNT(*) as count FROM users WHERE role = 'faculty'", one=True)['count']
        
        # Global attendance
        global_att = db_query("SELECT status FROM attendance")
        total_att = len(global_att)
        present_att = sum(1 for r in global_att if r['status'] == 'present')
        global_attendance_pct = (present_att / total_att * 100.0) if total_att > 0 else 100.0
        
        # Global syllabus progress
        total_topics = db_query("SELECT COUNT(*) as count FROM curriculum_topics", one=True)['count']
        completed_topics = db_query("SELECT COUNT(*) as count FROM curriculum_topics WHERE status = 'completed'", one=True)['count']
        global_curriculum_pct = (completed_topics / total_topics * 100.0) if total_topics > 0 else 0.0
        
        # Registration breakdown per activity
        activities = db_query("SELECT id, title, type, date, location FROM activities")
        act_data = []
        for act in activities:
            reg_count = db_query("SELECT COUNT(*) as count FROM activity_registrations WHERE activity_id = ?", (act['id'],), one=True)['count']
            cert_count = db_query("SELECT COUNT(*) as count FROM activity_registrations WHERE activity_id = ? AND certification_status = 'uploaded'", (act['id'],), one=True)['count']
            act_data.append({
                'id': act['id'],
                'title': act['title'],
                'type': act['type'],
                'date': act['date'],
                'location': act['location'],
                'registrations': reg_count,
                'pending_certs': cert_count
            })
            
        return jsonify({
            'total_students': total_students,
            'total_faculty': total_faculty,
            'avg_attendance_pct': round(global_attendance_pct, 1),
            'curriculum_pct': round(global_curriculum_pct, 1),
            'activities': act_data
        })
        
    return jsonify({'error': 'Invalid role'}), 400

# 3. ATTENDANCE MANAGEMENT
@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    student_id = request.args.get('student_id')
    subject_id = request.args.get('subject_id')
    faculty_id = request.args.get('faculty_id')
    
    if student_id:
        # Student viewing their own records
        query = '''
            SELECT a.id, s.name as subject_name, s.code as subject_code, a.date, a.status, a.verification_method
            FROM attendance a
            JOIN subjects s ON a.subject_id = s.id
            WHERE a.student_id = ?
            ORDER BY a.date DESC
        '''
        rows = db_query(query, (student_id,))
    elif subject_id:
        # Viewing class-wise records for a subject
        query = '''
            SELECT a.id, u.name as student_name, a.date, a.status, a.verification_method
            FROM attendance a
            JOIN users u ON a.student_id = u.id
            WHERE a.subject_id = ?
            ORDER BY a.date DESC, u.name ASC
        '''
        rows = db_query(query, (subject_id,))
    elif faculty_id:
        # Faculty viewing records for all subjects they teach
        query = '''
            SELECT a.id, s.code as subject_code, s.name as subject_name, u.name as student_name, a.date, a.status, a.verification_method
            FROM attendance a
            JOIN subjects s ON a.subject_id = s.id
            JOIN users u ON a.student_id = u.id
            WHERE s.faculty_id = ?
            ORDER BY a.date DESC, s.code ASC, u.name ASC
        '''
        rows = db_query(query, (faculty_id,))
    else:
        # Admin viewing everything
        query = '''
            SELECT a.id, s.code as subject_code, u.name as student_name, a.date, a.status, a.verification_method
            FROM attendance a
            JOIN subjects s ON a.subject_id = s.id
            JOIN users u ON a.student_id = u.id
            ORDER BY a.date DESC LIMIT 100
        '''
        rows = db_query(query)
        
    return jsonify([dict(r) for r in rows])

@app.route('/api/attendance/mark', methods=['POST'])
def mark_attendance():
    data = request.json or {}
    student_id = data.get('student_id')
    subject_id = data.get('subject_id')
    date = data.get('date')
    status = data.get('status')
    verification_method = data.get('verification_method', 'manual')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    if not student_id or not subject_id or not date or not status:
        return jsonify({'error': 'Missing required attendance fields'}), 400
        
    # GPS verification logic
    if verification_method == 'gps':
        if latitude is None or longitude is None:
            return jsonify({'error': 'GPS location required for verification'}), 400
        # Haversine or simple distance estimation
        # For simplicity, calculate absolute distance in degrees
        lat_diff = abs(float(latitude) - TARGET_LAT)
        lng_diff = abs(float(longitude) - TARGET_LNG)
        # 1 degree lat is ~111km. 0.0013 degrees is ~150 meters.
        if lat_diff > 0.0013 or lng_diff > 0.0013:
            return jsonify({
                'success': False, 
                'error': f'GPS Verification Failed. You are outside the classroom boundary. Proximity check failed (coordinates: {latitude}, {longitude}).'
            }), 403

    # QR Code & Face Recognition are simulated on the frontend but tracked here
    # Check if duplicate attendance for the same day and subject exists
    existing = db_query("SELECT id FROM attendance WHERE student_id = ? AND subject_id = ? AND date = ?", 
                        (student_id, subject_id, date), one=True)
                        
    if existing:
        db_commit("UPDATE attendance SET status = ?, verification_method = ?, latitude = ?, longitude = ? WHERE id = ?",
                  (status, verification_method, latitude, longitude, existing['id']))
        att_id = existing['id']
    else:
        att_id = db_commit('''
            INSERT INTO attendance (student_id, subject_id, date, status, verification_method, latitude, longitude)
            VALUES (?,?,?,?,?,?,?)
        ''', (student_id, subject_id, date, status, verification_method, latitude, longitude))
        
    return jsonify({
        'success': True,
        'attendance_id': att_id,
        'message': f'Attendance marked as {status} successfully via {verification_method.upper()}.'
    })

# 4. CURRICULUM SYLLABUS MANAGEMENT
@app.route('/api/curriculum', methods=['GET'])
def get_curriculum():
    subject_id = request.args.get('subject_id')
    faculty_id = request.args.get('faculty_id')
    
    if subject_id:
        rows = db_query("SELECT id, name, description, status, updated_at FROM curriculum_topics WHERE subject_id = ?", (subject_id,))
    elif faculty_id:
        rows = db_query('''
            SELECT t.id, t.subject_id, s.code as subject_code, s.name as subject_name, t.name, t.description, t.status, t.updated_at
            FROM curriculum_topics t
            JOIN subjects s ON t.subject_id = s.id
            WHERE s.faculty_id = ?
        ''', (faculty_id,))
    else:
        rows = db_query('''
            SELECT t.id, t.subject_id, s.code as subject_code, s.name as subject_name, t.name, t.description, t.status, t.updated_at
            FROM curriculum_topics t
            JOIN subjects s ON t.subject_id = s.id
        ''')
        
    return jsonify([dict(r) for r in rows])

@app.route('/api/curriculum/update', methods=['PUT'])
def update_curriculum():
    data = request.json or {}
    topic_id = data.get('topic_id')
    status = data.get('status')
    
    if not topic_id or not status:
        return jsonify({'error': 'Missing topic_id or status'}), 400
        
    now = datetime_str = datetime_str = os.popen('date /t').read().strip() # standard format
    # Using python datetime for clean standard format
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    db_commit("UPDATE curriculum_topics SET status = ?, updated_at = ? WHERE id = ?", (status, now_str, topic_id))
    return jsonify({'success': True, 'message': 'Curriculum status updated successfully.'})

# 5. ASSIGNMENTS & SUBMISSIONS
@app.route('/api/assignments', methods=['GET'])
def get_assignments():
    student_id = request.args.get('student_id')
    subject_id = request.args.get('subject_id')
    faculty_id = request.args.get('faculty_id')
    
    if student_id:
        # Return all assignments and any submission state for this student
        query = '''
            SELECT a.id, a.title, a.description, a.due_date, a.max_marks, s.code as subject_code, s.name as subject_name,
                   sub.file_name, sub.submission_date, sub.marks, sub.feedback, sub.id as submission_id
            FROM assignments a
            JOIN subjects s ON a.subject_id = s.id
            LEFT JOIN submissions sub ON a.id = sub.assignment_id AND sub.student_id = ?
            ORDER BY a.due_date ASC
        '''
        rows = db_query(query, (student_id,))
    elif subject_id:
        rows = db_query("SELECT id, title, description, due_date, max_marks FROM assignments WHERE subject_id = ?", (subject_id,))
    elif faculty_id:
        # Faculty seeing submissions for their subjects
        query = '''
            SELECT a.id as assignment_id, a.title, a.max_marks, s.code as subject_code,
                   sub.id as submission_id, u.name as student_name, sub.file_name, sub.submission_date, sub.marks, sub.feedback
            FROM assignments a
            JOIN subjects s ON a.subject_id = s.id
            JOIN submissions sub ON a.id = sub.assignment_id
            JOIN users u ON sub.student_id = u.id
            WHERE s.faculty_id = ?
            ORDER BY sub.submission_date DESC
        '''
        rows = db_query(query, (faculty_id,))
    else:
        rows = db_query("SELECT a.id, a.title, a.description, a.due_date, s.code as subject_code FROM assignments a JOIN subjects s ON a.subject_id = s.id")
        
    return jsonify([dict(r) for r in rows])

@app.route('/api/assignments/submit', methods=['POST'])
def submit_assignment():
    data = request.json or {}
    assignment_id = data.get('assignment_id')
    student_id = data.get('student_id')
    file_name = data.get('file_name', 'submission_attachment.pdf')
    
    if not assignment_id or not student_id:
        return jsonify({'error': 'Missing assignment_id or student_id'}), 400
        
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Check if submission already exists
    existing = db_query("SELECT id FROM submissions WHERE assignment_id = ? AND student_id = ?", 
                        (assignment_id, student_id), one=True)
                        
    if existing:
        db_commit("UPDATE submissions SET file_name = ?, submission_date = ?, marks = NULL, feedback = NULL WHERE id = ?",
                  (file_name, now_str, existing['id']))
        sub_id = existing['id']
    else:
        sub_id = db_commit('''
            INSERT INTO submissions (assignment_id, student_id, file_name, submission_date)
            VALUES (?,?,?,?)
        ''', (assignment_id, student_id, file_name, now_str))
        
    return jsonify({'success': True, 'submission_id': sub_id, 'message': 'Assignment submitted successfully.'})

@app.route('/api/assignments/grade', methods=['POST'])
def grade_assignment():
    data = request.json or {}
    submission_id = data.get('submission_id')
    marks = data.get('marks')
    feedback = data.get('feedback', '')
    
    if not submission_id or marks is None:
        return jsonify({'error': 'Missing submission_id or marks'}), 400
        
    db_commit("UPDATE submissions SET marks = ?, feedback = ? WHERE id = ?", (marks, feedback, submission_id))
    return jsonify({'success': True, 'message': 'Submission graded successfully.'})

@app.route('/api/assignments/create', methods=['POST'])
def create_assignment():
    data = request.json or {}
    subject_id = data.get('subject_id')
    title = data.get('title')
    description = data.get('description', '')
    due_date = data.get('due_date')
    max_marks = data.get('max_marks', 100)
    
    if not subject_id or not title or not due_date:
        return jsonify({'error': 'Missing subject_id, title, or due_date'}), 400
        
    assign_id = db_commit('''
        INSERT INTO assignments (subject_id, title, description, due_date, max_marks)
        VALUES (?,?,?,?,?)
    ''', (subject_id, title, description, due_date, max_marks))
    
    return jsonify({'success': True, 'assignment_id': assign_id, 'message': 'Assignment created successfully.'})

# 6. ACTIVITIES & CERTIFICATIONS
@app.route('/api/activities', methods=['GET'])
def get_activities():
    student_id = request.args.get('student_id')
    
    if student_id:
        # List all activities and check if student is registered
        query = '''
            SELECT a.id, a.title, a.type, a.date, a.description, a.location,
                   r.id as registration_id, r.certification_status, r.certificate_url
            FROM activities a
            LEFT JOIN activity_registrations r ON a.id = r.activity_id AND r.student_id = ?
            ORDER BY a.date ASC
        '''
        rows = db_query(query, (student_id,))
    else:
        rows = db_query("SELECT id, title, type, date, description, location FROM activities ORDER BY date ASC")
        
    return jsonify([dict(r) for r in rows])

@app.route('/api/activities/register', methods=['POST'])
def register_activity():
    data = request.json or {}
    activity_id = data.get('activity_id')
    student_id = data.get('student_id')
    
    if not activity_id or not student_id:
        return jsonify({'error': 'Missing activity_id or student_id'}), 400
        
    existing = db_query("SELECT id FROM activity_registrations WHERE activity_id = ? AND student_id = ?", 
                        (activity_id, student_id), one=True)
                        
    if existing:
        return jsonify({'success': False, 'error': 'Already registered for this activity.'}), 400
        
    reg_id = db_commit('''
        INSERT INTO activity_registrations (activity_id, student_id, certification_status)
        VALUES (?,?, 'none')
    ''', (activity_id, student_id))
    
    return jsonify({'success': True, 'registration_id': reg_id, 'message': 'Registered successfully.'})

@app.route('/api/activities/upload-cert', methods=['POST'])
def upload_certificate():
    data = request.json or {}
    registration_id = data.get('registration_id')
    certificate_url = data.get('certificate_url', 'uploads/certificate_attachment.pdf')
    
    if not registration_id:
        return jsonify({'error': 'Missing registration_id'}), 400
        
    db_commit("UPDATE activity_registrations SET certification_status = 'uploaded', certificate_url = ? WHERE id = ?",
              (certificate_url, registration_id))
              
    return jsonify({'success': True, 'message': 'Certificate uploaded. Waiting for admin verification.'})

@app.route('/api/activities/verify-cert', methods=['POST'])
def verify_certificate():
    data = request.json or {}
    registration_id = data.get('registration_id')
    status = data.get('status') # verified, none (denied)
    
    if not registration_id or not status:
        return jsonify({'error': 'Missing registration_id or status'}), 400
        
    db_commit("UPDATE activity_registrations SET certification_status = ? WHERE id = ?", (status, registration_id))
    return jsonify({'success': True, 'message': f'Certificate status updated to {status.upper()}.'})

# 7. AI & CHATBOT
@app.route('/api/ai/predictions', methods=['GET'])
def get_ai_predictions():
    # Returns ML predictions for all students
    students = db_query("SELECT id, name, username, email FROM users WHERE role = 'student'")
    results = []
    for s in students:
        pred = ml_engine.predict_student_status(s['id'])
        results.append({
            'student_id': s['id'],
            'name': s['name'],
            'username': s['username'],
            'email': s['email'],
            'attendance_rate': round(pred['features']['attendance_rate'], 1),
            'assignment_ratio': round(pred['features']['assignment_ratio'], 2),
            'avg_assignment_score': round(pred['features']['avg_assignment_score'], 1),
            'activity_count': pred['features']['activity_count'],
            'attendance_risk': pred['attendance_risk'],
            'risk_probability': round(pred['risk_probability'], 3),
            'predicted_final_score': pred['predicted_final_score'],
            'insight': pred['insight']
        })
    return jsonify(results)

@app.route('/api/ai/chat', methods=['POST'])
def chat():
    data = request.json or {}
    message = data.get('message')
    student_id = data.get('student_id')
    
    if not message or not student_id:
        return jsonify({'error': 'Missing message or student_id'}), 400
        
    response_text = process_chat_message(message, student_id)
    return jsonify({'response': response_text})

# 8. ADMIN USER MANAGEMENT
@app.route('/api/admin/users', methods=['GET'])
def get_all_users():
    users = db_query("SELECT id, username, name, role, email FROM users ORDER BY role, name")
    return jsonify([dict(u) for u in users])

@app.route('/api/admin/users/create', methods=['POST'])
def create_user():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password', 'temp123')
    name = data.get('name')
    role = data.get('role') # admin, faculty, student
    email = data.get('email')
    
    if not username or not name or not role or not email:
        return jsonify({'error': 'Missing required fields'}), 400
        
    try:
        user_id = db_commit('''
            INSERT INTO users (username, password, name, role, email)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, password, name, role, email))
        return jsonify({'success': True, 'user_id': user_id, 'message': 'User created successfully.'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Username already exists'}), 409

if __name__ == '__main__':
    print("Starting Smart Curriculum Flask Backend...")
    print(f"Serving static folder from: {FRONTEND_DIR}")
    # Run server locally on port 5000
    app.run(host='127.0.0.1', port=5000, debug=True)
