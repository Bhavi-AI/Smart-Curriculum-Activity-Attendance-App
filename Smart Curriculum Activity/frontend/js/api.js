/*
================================================================
   SMART CURRICULUM APP FRONTEND API MODULE (api.js)
================================================================
*/

const BASE_URL = ''; // Same-origin, served directly by Flask

const api = {
    // 1. AUTHENTICATION
    async login(username, password) {
        const response = await fetch(`${BASE_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        return response.json();
    },

    // 2. DASHBOARD STATS
    async getStats(role, userId) {
        const response = await fetch(`${BASE_URL}/api/dashboard/stats?role=${role}&user_id=${userId}`);
        return response.json();
    },

    // 3. ATTENDANCE
    async getAttendance(params = {}) {
        const query = new URLSearchParams(params).toString();
        const response = await fetch(`${BASE_URL}/api/attendance?${query}`);
        return response.json();
    },

    async markAttendance(data) {
        const response = await fetch(`${BASE_URL}/api/attendance/mark`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    // 4. CURRICULUM SYLLABUS
    async getCurriculum(params = {}) {
        const query = new URLSearchParams(params).toString();
        const response = await fetch(`${BASE_URL}/api/curriculum?${query}`);
        return response.json();
    },

    async updateCurriculum(topicId, status) {
        const response = await fetch(`${BASE_URL}/api/curriculum/update`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic_id: topicId, status })
        });
        return response.json();
    },

    // 5. ASSIGNMENTS & GRADING
    async getAssignments(params = {}) {
        const query = new URLSearchParams(params).toString();
        const response = await fetch(`${BASE_URL}/api/assignments?${query}`);
        return response.json();
    },

    async submitAssignment(assignmentId, studentId, fileName) {
        const response = await fetch(`${BASE_URL}/api/assignments/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ assignment_id: assignmentId, student_id: studentId, file_name: fileName })
        });
        return response.json();
    },

    async gradeAssignment(submissionId, marks, feedback) {
        const response = await fetch(`${BASE_URL}/api/assignments/grade`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ submission_id: submissionId, marks, feedback })
        });
        return response.json();
    },

    async createAssignment(subjectId, title, description, dueDate, maxMarks) {
        const response = await fetch(`${BASE_URL}/api/assignments/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ subject_id: subjectId, title, description, due_date: dueDate, max_marks: maxMarks })
        });
        return response.json();
    },

    // 6. ACTIVITIES & CERTIFICATIONS
    async getActivities(studentId = null) {
        const url = studentId ? `${BASE_URL}/api/activities?student_id=${studentId}` : `${BASE_URL}/api/activities`;
        const response = await fetch(url);
        return response.json();
    },

    async registerActivity(activityId, studentId) {
        const response = await fetch(`${BASE_URL}/api/activities/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ activity_id: activityId, student_id: studentId })
        });
        return response.json();
    },

    async uploadCertificate(registrationId, certificateUrl) {
        const response = await fetch(`${BASE_URL}/api/activities/upload-cert`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ registration_id: registrationId, certificate_url: certificateUrl })
        });
        return response.json();
    },

    async verifyCertificate(registrationId, status) {
        const response = await fetch(`${BASE_URL}/api/activities/verify-cert`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ registration_id: registrationId, status })
        });
        return response.json();
    },

    // 7. AI ENGINE
    async getAIPredictions() {
        const response = await fetch(`${BASE_URL}/api/ai/predictions`);
        return response.json();
    },

    async sendChat(message, studentId) {
        const response = await fetch(`${BASE_URL}/api/ai/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, student_id: studentId })
        });
        return response.json();
    },

    // 8. ADMIN USER MANAGEMENT
    async getUsers() {
        const response = await fetch(`${BASE_URL}/api/admin/users`);
        return response.json();
    },

    async createUser(userData) {
        const response = await fetch(`${BASE_URL}/api/admin/users/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });
        return response.json();
    }
};
