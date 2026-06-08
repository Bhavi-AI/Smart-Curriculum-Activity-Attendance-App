import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "curriculum_tracker.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # If database file already exists, we will overwrite/re-create to ensure fresh seed
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        role TEXT NOT NULL, -- admin, faculty, student
        email TEXT NOT NULL
    )
    ''')
    
    # 2. Subjects Table
    cursor.execute('''
    CREATE TABLE subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        faculty_id INTEGER,
        FOREIGN KEY (faculty_id) REFERENCES users (id)
    )
    ''')
    
    # 3. Curriculum Topics Table
    cursor.execute('''
    CREATE TABLE curriculum_topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'pending', -- pending, completed
        updated_at TEXT,
        FOREIGN KEY (subject_id) REFERENCES subjects (id)
    )
    ''')
    
    # 4. Attendance Table
    cursor.execute('''
    CREATE TABLE attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL, -- present, absent
        verification_method TEXT NOT NULL, -- manual, qr, face, gps
        latitude REAL,
        longitude REAL,
        FOREIGN KEY (student_id) REFERENCES users (id),
        FOREIGN KEY (subject_id) REFERENCES subjects (id)
    )
    ''')
    
    # 5. Activities Table
    cursor.execute('''
    CREATE TABLE activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        type TEXT NOT NULL, -- club, workshop, sports
        date TEXT NOT NULL,
        description TEXT,
        location TEXT NOT NULL
    )
    ''')
    
    # 6. Activity Registrations Table
    cursor.execute('''
    CREATE TABLE activity_registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        certification_status TEXT NOT NULL DEFAULT 'none', -- none, uploaded, verified
        certificate_url TEXT,
        FOREIGN KEY (activity_id) REFERENCES activities (id),
        FOREIGN KEY (student_id) REFERENCES users (id)
    )
    ''')
    
    # 7. Assignments Table
    cursor.execute('''
    CREATE TABLE assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        due_date TEXT NOT NULL,
        max_marks INTEGER NOT NULL,
        FOREIGN KEY (subject_id) REFERENCES subjects (id)
    )
    ''')
    
    # 8. Submissions Table
    cursor.execute('''
    CREATE TABLE submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        file_name TEXT,
        submission_date TEXT NOT NULL,
        marks INTEGER, -- NULL if ungraded
        feedback TEXT,
        FOREIGN KEY (assignment_id) REFERENCES assignments (id),
        FOREIGN KEY (student_id) REFERENCES users (id)
    )
    ''')
    
    # --- SEED DATA ---
    
    # 1. Users
    users_data = [
        # Admin
        ('admin', 'admin123', 'System Administrator', 'admin', 'admin@smartcurriculum.edu'),
        # Faculty
        ('faculty_turing', 'faculty123', 'Dr. Alan Turing', 'faculty', 'turing@smartcurriculum.edu'),
        ('faculty_curie', 'faculty123', 'Dr. Marie Curie', 'faculty', 'curie@smartcurriculum.edu'),
        ('faculty_shakespeare', 'faculty123', 'Prof. William Shakespeare', 'faculty', 'shakespeare@smartcurriculum.edu'),
        # Students
        ('student_john', 'student123', 'John Doe', 'student', 'john.doe@smartcurriculum.edu'),
        ('student_jane', 'student123', 'Jane Smith', 'student', 'jane.smith@smartcurriculum.edu'),
        ('student_bob', 'student123', 'Bob Johnson', 'student', 'bob.johnson@smartcurriculum.edu'),
        ('student_alice', 'student123', 'Alice Williams', 'student', 'alice.williams@smartcurriculum.edu'),
        ('student_charlie', 'student123', 'Charlie Brown', 'student', 'charlie.brown@smartcurriculum.edu')
    ]
    cursor.executemany('INSERT INTO users (username, password, name, role, email) VALUES (?,?,?,?,?)', users_data)
    
    # 2. Subjects (faculty mapping by ID)
    # Dr Alan Turing: id=2 (CS-101, MA-101)
    # Dr Marie Curie: id=3 (PH-101)
    # Prof Shakespeare: id=4 (EN-101)
    subjects_data = [
        ('Computer Science I', 'CS-101', 2),
        ('Discrete Mathematics', 'MA-101', 2),
        ('Quantum Physics Intro', 'PH-101', 3),
        ('English Literature & Composition', 'EN-101', 4)
    ]
    cursor.executemany('INSERT INTO subjects (name, code, faculty_id) VALUES (?,?,?)', subjects_data)
    
    # 3. Curriculum Topics (5 topics per subject)
    topics_data = [
        # CS-101 Topics
        (1, 'Variables & Control Flow', 'Introduction to basic programming structures', 'completed', '2026-05-10 10:00:00'),
        (1, 'Functions & Modular Design', 'Writing reusable functions and arguments passing', 'completed', '2026-05-18 11:30:00'),
        (1, 'Data Structures: Lists & Sets', 'Handling primitive collections in memory', 'completed', '2026-06-01 09:45:00'),
        (1, 'Object-Oriented Programming', 'Classes, objects, inheritance, and encapsulation', 'pending', None),
        (1, 'File I/O and Error Handling', 'Reading and writing external files safely', 'pending', None),
        
        # MA-101 Topics
        (2, 'Set Theory & Venn Diagrams', 'Operations on sets and Venn diagrams', 'completed', '2026-05-12 14:00:00'),
        (2, 'Propositional Logic', 'Truth tables, logical equivalences, and quantifiers', 'completed', '2026-05-26 15:15:00'),
        (2, 'Relations & Functions', 'Equivalence relations, functions properties', 'pending', None),
        (2, 'Graph Theory Basics', 'Nodes, edges, paths, and Eulerian paths', 'pending', None),
        (2, 'Combinatorics & Probability', 'Permutations, combinations, and basic probability', 'pending', None),
        
        # PH-101 Topics
        (3, 'Wave-Particle Duality', 'Photoelectric effect and double-slit experiment', 'completed', '2026-05-15 13:00:00'),
        (3, 'Schrodinger Equation', 'Introduction to wave functions and probability density', 'completed', '2026-05-29 14:30:00'),
        (3, 'Quantum Tunneling', 'Particles crossing potential energy barriers', 'pending', None),
        (3, 'Atomic Spectra & Bohr Model', 'Energy levels and spectral line emissions', 'pending', None),
        (3, 'Quantum Entanglement', 'Spooky action at a distance, Bell inequalities', 'pending', None),
        
        # EN-101 Topics
        (4, 'The Shakespearean Drama', 'Analyzing tragedy in Hamlet and Macbeth', 'completed', '2026-05-11 11:00:00'),
        (4, 'Victorian Era Poetry', 'Themes of industry, morality, and romanticism', 'completed', '2026-05-25 11:45:00'),
        (4, 'Modernist Literature Flow', 'Stream of consciousness in Joyce and Woolf', 'completed', '2026-06-05 12:00:00'),
        (4, 'Narrative Perspectives', 'First-person, third-person limited, and omniscient voice', 'completed', '2026-06-07 10:30:00'),
        (4, 'Rhetoric & Argumentation Essay', 'Constructing a persuasive analytical thesis statement', 'pending', None)
    ]
    cursor.executemany('INSERT INTO curriculum_topics (subject_id, name, description, status, updated_at) VALUES (?,?,?,?,?)', topics_data)
    
    # 4. Attendance
    # Seed historical attendance for the last 4 weeks (say 12 lecture dates)
    # Lecture dates: May 11, May 13, May 15, May 18, May 20, May 22, May 25, May 27, May 29, June 1, June 3, June 5 (2026)
    lecture_dates = [
        '2026-05-11', '2026-05-13', '2026-05-15', '2026-05-18', '2026-05-20', 
        '2026-05-22', '2026-05-25', '2026-05-27', '2026-05-29', '2026-06-01', 
        '2026-06-03', '2026-06-05'
    ]
    
    # Student IDs: 5 (John), 6 (Jane), 7 (Bob), 8 (Alice), 9 (Charlie)
    # Subject IDs: 1 (CS-101), 2 (MA-101), 3 (PH-101), 4 (EN-101)
    
    attendance_records = []
    
    # Define attendance profile for each student to train ML models later
    # John: Excellent (~92% attendance)
    # Jane: Boarderline (~75% attendance)
    # Bob: Low (~45% attendance)
    # Alice: Perfect (100% attendance)
    # Charlie: Average (~66% attendance)
    import random
    random.seed(42) # Seed for reproducible results
    
    profiles = {
        5: 0.92, # John
        6: 0.75, # Jane
        7: 0.45, # Bob
        8: 1.00, # Alice
        9: 0.66  # Charlie
    }
    
    methods = ['manual', 'qr', 'face', 'gps']
    
    # Coordinates of the classroom (centered near a hypothetical campus building)
    class_lat, class_lng = 12.9716, 77.5946
    
    for s_id, rate in profiles.items():
        for sub_id in [1, 2, 3, 4]:
            for date in lecture_dates:
                is_present = random.random() < rate
                status = 'present' if is_present else 'absent'
                method = random.choice(methods) if is_present else 'manual'
                
                # Introduce slight GPS deviations for present records, and big deviation or none for absent
                if is_present:
                    lat = class_lat + random.uniform(-0.0001, 0.0001)
                    lng = class_lng + random.uniform(-0.0001, 0.0001)
                else:
                    lat = None
                    lng = None
                    
                attendance_records.append((s_id, sub_id, date, status, method, lat, lng))
                
    cursor.executemany('''
    INSERT INTO attendance (student_id, subject_id, date, status, verification_method, latitude, longitude)
    VALUES (?,?,?,?,?,?,?)
    ''', attendance_records)
    
    # 5. Activities
    activities_data = [
        ('Campus Hackathon 2026', 'workshop', '2026-06-12', '48-hour prototype challenge for smart solutions', 'Main Auditorium'),
        ('Robotics and IoT Seminar', 'workshop', '2026-06-18', 'Learn the basics of microcontrollers and automation', 'Engineering Lab 4'),
        ('Annual Inter-College Sports Meet', 'sports', '2026-06-25', 'Compete in Athletics, Football, and Basketball events', 'Campus Sports Ground'),
        ('Google Developer Club Kickoff', 'club', '2026-06-04', 'Introductory session and workshop on cloud APIs', 'Seminar Hall B')
    ]
    cursor.executemany('INSERT INTO activities (title, type, date, description, location) VALUES (?,?,?,?,?)', activities_data)
    
    # 6. Activity Registrations
    # Seeding registrations and certificate uploads
    registrations = [
        # John (5) registered for Hackathon and Google Club (already happened)
        (1, 5, 'none', None),
        (4, 5, 'verified', 'uploads/john_gcp_cert.pdf'),
        # Jane (6) registered for Hackathon
        (1, 6, 'none', None),
        # Bob (7) registered for Sports
        (3, 7, 'none', None),
        # Alice (8) registered for Robotics Seminar and Google Club
        (2, 8, 'uploaded', 'uploads/alice_robotics_stub.pdf'),
        (4, 8, 'verified', 'uploads/alice_gcp_cert.pdf'),
        # Charlie (9) registered for Sports
        (3, 9, 'verified', 'uploads/charlie_sports_cert.pdf')
    ]
    cursor.executemany('INSERT INTO activity_registrations (activity_id, student_id, certification_status, certificate_url) VALUES (?,?,?,?)', registrations)
    
    # 7. Assignments
    # Create 3 assignments for subjects
    assignments_data = [
        # CS-101 (Subject 1)
        (1, 'Python Web Page Server', 'Build a simple web page using python built-in server', '2026-05-20', 100),
        (1, 'Algorithm Flowchart & Complexity', 'Submit a flowchart detailing quicksort complexity', '2026-06-04', 100),
        (1, 'Interactive Command App', 'Develop a CLI tool for curriculum task tracking', '2026-06-15', 100),
        
        # MA-101 (Subject 2)
        (2, 'Logical Truth Tables Proofs', 'Solve truth table problems on propositional proofs', '2026-05-25', 50),
        (2, 'Graph Coloring Theorem Homework', 'Submit proof for the 4-color theorem boundaries', '2026-06-12', 50),
        
        # PH-101 (Subject 3)
        (3, 'Double Slit Experiment Calculus', 'Calculate fringe widths for specific light frequencies', '2026-05-30', 100),
        (3, 'Schrodinger Infinite Well Analysis', 'Solve wave equations for particle in a 1D box', '2026-06-20', 100)
    ]
    cursor.executemany('INSERT INTO assignments (subject_id, title, description, due_date, max_marks) VALUES (?,?,?,?,?)', assignments_data)
    
    # 8. Submissions
    # Grade distribution matches the profiles
    # John (5): High marks
    # Jane (6): High marks
    # Bob (7): Low marks or missing
    # Alice (8): Average to High
    # Charlie (9): Low/Average
    submissions_data = [
        # CS-101 Assignment 1 (Python Web Page Server) - due 2026-05-20
        (1, 5, 'john_webserver.py', '2026-05-19 22:00:00', 95, 'Excellent clean implementation.'),
        (1, 6, 'jane_server.py', '2026-05-20 12:00:00', 88, 'Good structure, missing some MIME types.'),
        (1, 7, 'bob_server_attempt.py', '2026-05-22 14:00:00', 45, 'Late submission, code has syntax errors.'), # Bob late and low
        (1, 8, 'alice_web.py', '2026-05-20 09:00:00', 92, 'Well commented and structured.'),
        (1, 9, 'charlie_server.py', '2026-05-20 18:00:00', 65, 'Implemented basic server but lacks styling.'),
        
        # CS-101 Assignment 2 (Algorithm Flowchart) - due 2026-06-04
        (2, 5, 'john_algorithms.pdf', '2026-06-03 14:00:00', 98, 'Flawless analysis.'),
        (2, 6, 'jane_complexity.pdf', '2026-06-04 11:00:00', 90, 'Clear diagram flow.'),
        # Bob (7) did NOT submit Assignment 2
        (2, 8, 'alice_flowchart.pdf', '2026-06-04 15:00:00', 85, 'Good flowchart, minor arithmetic mistakes.'),
        (2, 9, 'charlie_complexity.pdf', '2026-06-04 23:59:00', 60, 'Sloppy layout, but correctly derived bounds.'),
        
        # MA-101 Assignment 4 (Logical Truth Tables) - due 2026-05-25
        (4, 5, 'john_logic.pdf', '2026-05-24 10:00:00', 49, 'Superb.'),
        (4, 6, 'jane_logic.pdf', '2026-05-25 14:00:00', 45, 'Great work.'),
        (4, 7, 'bob_logic.pdf', '2026-05-26 10:00:00', 20, 'Very poor attempts, failed half the proofs.'),
        (4, 8, 'alice_tables.pdf', '2026-05-25 15:30:00', 44, 'Very neat truth tables.'),
        (4, 9, 'charlie_logic_hw.pdf', '2026-05-25 17:00:00', 32, 'Many logical fallacies in questions 3 & 4.')
    ]
    cursor.executemany('''
    INSERT INTO submissions (assignment_id, student_id, file_name, submission_date, marks, feedback)
    VALUES (?,?,?,?,?,?)
    ''', submissions_data)
    
    conn.commit()
    conn.close()
    print("Database successfully initialized and seeded at:", DB_PATH)

if __name__ == '__main__':
    init_db()
