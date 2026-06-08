import sqlite3
import os
import re
from ml_engine import ml_engine

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "curriculum_tracker.db")

def query_db(query, params=(), one=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return (rows[0] if rows else None) if one else rows

def process_chat_message(message, student_id):
    msg = message.lower().strip()
    
    # Get student name
    student_row = query_db("SELECT name FROM users WHERE id = ?", (student_id,), one=True)
    student_name = student_row['name'] if student_row else "Student"
    
    # 1. GREETING INTENT
    if re.search(r'\b(hi|hello|hey|greetings|yo|welcome)\b', msg):
        return (f"Hello {student_name}! I am your Smart Curriculum AI Assistant. "
                "You can ask me questions like:\n"
                "- 'What is my attendance?'\n"
                "- 'Which assignments are pending?'\n"
                "- 'What are my marks?'\n"
                "- 'Predict my final grade' or 'Am I at risk of failing?'\n"
                "- 'What upcoming activities do I have?'")
                
    # 2. ATTENDANCE INTENT
    elif re.search(r'\b(attendance|present|absent|classes|class)\b', msg):
        rows = query_db('''
            SELECT s.code, s.name, 
                   SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as present_count,
                   COUNT(a.status) as total_count
            FROM attendance a
            JOIN subjects s ON a.subject_id = s.id
            WHERE a.student_id = ?
            GROUP BY s.id
        ''', (student_id,))
        
        if not rows:
            return "No attendance records found for you in the database."
            
        response = f"Here is your subject-wise attendance breakdown, {student_name}:\n\n"
        total_present = 0
        total_classes = 0
        
        for r in rows:
            code = r['code']
            present = r['present_count']
            total = r['total_count']
            rate = (present / total * 100.0) if total > 0 else 0
            total_present += present
            total_classes += total
            
            warning_emoji = "⚠️" if rate < 75 else "✅"
            response += f"- **{code}**: {rate:.1f}% ({present}/{total} classes) {warning_emoji}\n"
            
        overall_rate = (total_present / total_classes * 100.0) if total_classes > 0 else 0
        response += f"\n**Overall Attendance Rate**: {overall_rate:.1f}%"
        if overall_rate < 75:
            response += " ⚠️ (Below required 75% threshold. Please attend more classes!)"
        else:
            response += " ✅ (Good job keeping it above 75%!)"
        return response
        
    # 3. PENDING ASSIGNMENTS INTENT
    elif re.search(r'\b(assignment|assignments|pending|homework|homeworks|submit|due)\b', msg):
        # Fetch assignments that have NOT been submitted by the student
        # Total assignments minus student submissions
        rows = query_db('''
            SELECT a.title, a.due_date, s.code
            FROM assignments a
            JOIN subjects s ON a.subject_id = s.id
            LEFT JOIN submissions sub ON a.id = sub.assignment_id AND sub.student_id = ?
            WHERE sub.id IS NULL
            ORDER BY a.due_date ASC
        ''', (student_id,))
        
        if not rows:
            return "🎉 Excellent! You have **no pending assignments** at the moment."
            
        response = f"You have **{len(rows)} pending assignment(s)**, {student_name}:\n\n"
        for r in rows:
            response += f"- **{r['title']}** ({r['code']}) — Due: *{r['due_date']}*\n"
        response += "\nYou can upload and submit them directly from the Assignments tab."
        return response

    # 4. GRADES / MARKS INTENT
    elif re.search(r'\b(marks|grades|score|scores|result|results|exam|performance)\b', msg):
        rows = query_db('''
            SELECT a.title, s.code, sub.marks, a.max_marks, sub.feedback
            FROM submissions sub
            JOIN assignments a ON sub.assignment_id = a.id
            JOIN subjects s ON a.subject_id = s.id
            WHERE sub.student_id = ?
        ''', (student_id,))
        
        if not rows:
            return "No graded submissions found in your academic record yet."
            
        response = f"Here are your graded assignments, {student_name}:\n\n"
        scores = []
        for r in rows:
            marks = r['marks']
            max_m = r['max_marks']
            pct = (marks / max_m * 100.0) if max_m > 0 else 0
            scores.append(pct)
            
            response += f"- **{r['title']}** ({r['code']}): **{marks}/{max_m}** ({pct:.1f}%) \n"
            if r['feedback']:
                response += f"  *Feedback: \"{r['feedback']}\"*\n"
                
        avg_score = sum(scores) / len(scores) if scores else 0
        response += f"\n**Average Grade**: {avg_score:.1f}%"
        if avg_score < 60:
            response += " ⚠️ (Focus on upcoming reviews to pull up your averages)."
        return response

    # 5. AI PREDICTION INTENT
    elif re.search(r'\b(predict|prediction|risk|fail|at risk|pass|future|score prediction)\b', msg):
        res = ml_engine.predict_student_status(student_id)
        
        response = f"🤖 **AI Academic Performance Forecast** for {student_name}:\n\n"
        response += f"- **Predicted Final Grade**: `{res['predicted_final_score']}%` 📈\n"
        
        risk_status = res['attendance_risk']
        prob = res['risk_probability']
        
        if risk_status == "At Risk":
            response += f"- **Attendance Status**: `At Risk` ⚠️ (Predicted probability of low attendance: `{prob * 100:.1f}%`)\n"
        else:
            response += f"- **Attendance Status**: `Safe` ✅ (Predicted probability of low attendance: `{prob * 100:.1f}%`)\n"
            
        response += f"\n💡 **AI Analytics Insight**: *\"{res['insight']}\"*"
        return response

    # 6. ACTIVITIES INTENT
    elif re.search(r'\b(activities|activity|workshop|seminar|club|sports|event|events)\b', msg):
        # Fetch registered upcoming activities
        rows = query_db('''
            SELECT act.title, act.type, act.date, act.location, reg.certification_status
            FROM activity_registrations reg
            JOIN activities act ON reg.activity_id = act.id
            WHERE reg.student_id = ?
        ''', (student_id,))
        
        if not rows:
            return "You are not registered for any upcoming activities or workshops. Visit the Activity Hub to register!"
            
        response = f"Here are your registered activities, {student_name}:\n\n"
        for r in rows:
            type_badge = r['type'].capitalize()
            status_badge = ""
            if r['certification_status'] == 'verified':
                status_badge = "✅ (Certificate Verified)"
            elif r['certification_status'] == 'uploaded':
                status_badge = "⏳ (Certificate Under Review)"
            else:
                status_badge = "📅 (Registered - Upcoming)"
                
            response += f"- **{r['title']}** ({type_badge}) — Date: *{r['date']}* at {r['location']} {status_badge}\n"
        return response

    # 7. HELP / FALLBACK
    else:
        return (f"Sorry, {student_name}, I didn't quite catch that. "
                "I am trained specifically on your academic records. Try asking:\n"
                "- 'What is my current attendance rate?'\n"
                "- 'Are there any pending assignments due?'\n"
                "- 'What is my grade prediction?'\n"
                "- 'What workshops or seminars am I attending?'")

if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
        
    # Test chatbot with Bob (ID 7)
    test_id = 7
    print("Greeting test:")
    print(process_chat_message("hello there!", test_id))
    print("\nAttendance test:")
    print(process_chat_message("tell me about my attendance?", test_id))
    print("\nPending assignments test:")
    print(process_chat_message("do I have any pending assignments?", test_id))
    print("\nAI Prediction test:")
    print(process_chat_message("am I at risk or will I pass?", test_id))
