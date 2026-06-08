import numpy as np
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "curriculum_tracker.db")

class CustomStandardScaler:
    def __init__(self):
        self.mean = None
        self.std = None
        
    def fit(self, X):
        self.mean = np.mean(X, axis=0)
        self.std = np.std(X, axis=0)
        # Prevent division by zero
        self.std = np.where(self.std == 0, 1.0, self.std)
        return self
        
    def transform(self, X):
        return (X - self.mean) / self.std
        
    def fit_transform(self, X):
        self.fit(X)
        return self.transform(X)

class CustomLogisticRegression:
    def __init__(self, lr=0.1, epochs=1000):
        self.lr = lr
        self.epochs = epochs
        self.w = None
        self.b = None
        
    def _sigmoid(self, z):
        z = np.clip(z, -25, 25) # prevent overflow
        return 1.0 / (1.0 + np.exp(-z))
        
    def fit(self, X, y):
        m, n = X.shape
        self.w = np.zeros(n)
        self.b = 0.0
        
        for _ in range(self.epochs):
            z = np.dot(X, self.w) + self.b
            y_pred = self._sigmoid(z)
            
            dw = (1/m) * np.dot(X.T, (y_pred - y))
            db = (1/m) * np.sum(y_pred - y)
            
            self.w -= self.lr * dw
            self.b -= self.lr * db
            
    def predict_proba(self, X):
        z = np.dot(X, self.w) + self.b
        prob = self._sigmoid(z)
        # returns [[prob_0, prob_1]]
        return np.column_stack((1.0 - prob, prob))
        
    def predict(self, X):
        prob = self.predict_proba(X)[:, 1]
        return (prob >= 0.5).astype(int)

class CustomLinearRegression:
    def __init__(self):
        self.w = None
        
    def fit(self, X, y):
        m, n = X.shape
        # Add column of ones for bias
        X_design = np.column_stack((np.ones(m), X))
        
        # Ridge regression closed-form: w = (X_d.T * X_d + lambda * I)^-1 * X_d.T * y
        identity = np.eye(n + 1)
        identity[0, 0] = 0.0 # do not regularize bias term
        
        A = np.dot(X_design.T, X_design) + 1e-4 * identity
        b = np.dot(X_design.T, y)
        self.w = np.linalg.solve(A, b)
        
    def predict(self, X):
        m = X.shape[0]
        X_design = np.column_stack((np.ones(m), X))
        return np.dot(X_design, self.w)

class MLEngine:
    def __init__(self):
        self.attendance_scaler = CustomStandardScaler()
        self.attendance_model = CustomLogisticRegression(lr=0.1, epochs=1000)
        
        self.performance_scaler = CustomStandardScaler()
        self.performance_model = CustomLinearRegression()
        
        # Train models immediately on initialization
        self.train_models()

    def generate_synthetic_data(self, n_samples=500):
        """
        Generates synthetic data with correlated variables:
        Features:
          - attendance_rate: 0 to 100 (float)
          - assignment_ratio: 0 to 1.0 (float)
          - avg_assignment_score: 0 to 100 (float)
          - activity_count: 0 to 5 (integer)
        Targets:
          - at_risk (attendance risk < 75%): 0 or 1
          - final_score: 0 to 100 (float)
        """
        np.random.seed(42)
        
        # Base diligence factor (0 to 1)
        diligence = np.random.uniform(0, 1, n_samples)
        
        # Features: correlated with diligence
        attendance_rate = 30 + 70 * diligence + np.random.normal(0, 5, n_samples)
        attendance_rate = np.clip(attendance_rate, 0.0, 100.0)
        
        assignment_ratio = diligence + np.random.normal(0, 0.1, n_samples)
        assignment_ratio = np.clip(assignment_ratio, 0.0, 1.0)
        
        avg_assignment_score = 40 + 60 * diligence + np.random.normal(0, 8, n_samples)
        avg_assignment_score = np.clip(avg_assignment_score, 0.0, 100.0)
        
        activity_count = np.round(diligence * 4 + np.random.normal(0, 0.5, n_samples))
        activity_count = np.clip(activity_count, 0, 5).astype(int)
        
        # Targets
        # Risk target: 1 if current attendance < 75% or diligence is extremely low + noise
        risk_score = 1.0 - (attendance_rate / 100.0) * 0.7 - diligence * 0.3
        at_risk = (risk_score > 0.45).astype(int)
        
        # Academic score target: correlated with attendance, assignments, and activities
        final_score = (0.35 * attendance_rate + 
                       0.45 * avg_assignment_score + 
                       12 * assignment_ratio + 
                       1.5 * activity_count + 
                       np.random.normal(0, 2, n_samples))
        final_score = np.clip(final_score, 0.0, 100.0)
        
        X = np.column_stack((attendance_rate, assignment_ratio, avg_assignment_score, activity_count))
        
        return X, at_risk, final_score

    def train_models(self):
        """
        Train the custom ML prediction models.
        """
        try:
            X, y_att, y_perf = self.generate_synthetic_data(500)
            
            # Train attendance risk classification model
            X_att_scaled = self.attendance_scaler.fit_transform(X)
            self.attendance_model.fit(X_att_scaled, y_att)
            
            # Train academic performance regression model
            X_perf_scaled = self.performance_scaler.fit_transform(X)
            self.performance_model.fit(X_perf_scaled, y_perf)
            
            print("Custom ML Models (Logistic & Linear Regression) successfully trained using NumPy.")
        except Exception as e:
            print("Error training ML models:", e)

    def get_student_features(self, student_id):
        """
        Queries the database to compute features for a specific student.
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Compute attendance rate
        cursor.execute("SELECT status FROM attendance WHERE student_id = ?", (student_id,))
        rows = cursor.fetchall()
        if not rows:
            attendance_rate = 75.0
        else:
            present = sum(1 for row in rows if row[0] == 'present')
            attendance_rate = (present / len(rows)) * 100.0
            
        # 2. Compute assignment submission ratio & average score
        cursor.execute("SELECT COUNT(*) FROM assignments")
        total_assignments = cursor.fetchone()[0]
        if total_assignments == 0:
            total_assignments = 1
            
        cursor.execute("SELECT marks, max_marks FROM submissions s JOIN assignments a ON s.assignment_id = a.id WHERE student_id = ?", (student_id,))
        subs = cursor.fetchall()
        
        submitted_count = len(subs)
        assignment_ratio = submitted_count / total_assignments
        
        if submitted_count == 0:
            avg_score = 50.0
        else:
            normalized_scores = []
            for marks, max_marks in subs:
                if marks is not None and max_marks > 0:
                    normalized_scores.append((marks / max_marks) * 100.0)
            avg_score = np.mean(normalized_scores) if normalized_scores else 50.0
            
        # 3. Compute activity registrations
        cursor.execute("SELECT COUNT(*) FROM activity_registrations WHERE student_id = ?", (student_id,))
        activity_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'attendance_rate': float(attendance_rate),
            'assignment_ratio': float(assignment_ratio),
            'avg_assignment_score': float(avg_score),
            'activity_count': int(activity_count)
        }

    def predict_student_status(self, student_id):
        """
        Runs custom ML prediction for a given student ID.
        """
        feats = self.get_student_features(student_id)
        
        input_data = np.array([[
            feats['attendance_rate'],
            feats['assignment_ratio'],
            feats['avg_assignment_score'],
            feats['activity_count']
        ]])
        
        # 1. Attendance Risk Prediction
        input_att_scaled = self.attendance_scaler.transform(input_data)
        risk_prob = self.attendance_model.predict_proba(input_att_scaled)[0][1]
        
        # Categorize
        is_at_risk = "At Risk" if (risk_prob > 0.45 or feats['attendance_rate'] < 75.0) else "Safe"
        
        # 2. Performance Grade Prediction
        input_perf_scaled = self.performance_scaler.transform(input_data)
        predicted_grade = self.performance_model.predict(input_perf_scaled)[0]
        predicted_grade = float(np.clip(predicted_grade, 0.0, 100.0))
        
        # Actionable AI Insight tip
        if is_at_risk == "At Risk":
            insight = "Attendance risk detected. Attending the next few classes is critical to raise the attendance above 75%."
        elif feats['assignment_ratio'] < 0.8:
            insight = "Submitting pending assignments could raise your final predicted grade by up to 8%."
        elif feats['avg_assignment_score'] < 70:
            insight = "Reviewing assignment feedback and concepts with Dr. Alan Turing could help raise homework scores."
        else:
            insight = "Outstanding progress! High attendance and homework marks predict a strong final grade."
            
        return {
            'student_id': student_id,
            'features': feats,
            'attendance_risk': is_at_risk,
            'risk_probability': float(risk_prob),
            'predicted_final_score': round(predicted_grade, 1),
            'insight': insight
        }

# Singleton instance
ml_engine = MLEngine()

if __name__ == '__main__':
    # Test predictions
    for s_id, name in [(5, "John Doe"), (7, "Bob Johnson")]:
        res = ml_engine.predict_student_status(s_id)
        print(f"\n--- Custom ML Prediction Test for {name} (ID {s_id}) ---")
        print(f"Features: {res['features']}")
        print(f"Attendance Risk: {res['attendance_risk']} (Probability: {res['risk_probability']:.2f})")
        print(f"Predicted Final Grade: {res['predicted_final_score']}%")
        print(f"AI Insight: {res['insight']}")
