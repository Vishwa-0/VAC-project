// Dynamic API Base URL detection
const API_BASE_URL = window.location.origin;

// Application State
let currentUser = null;
let activeRole = 'student'; // student, instructor, admin
let authMode = 'signin';     // signin, signup
let currentCourseId = 'devops';
let activeLessonIndex = 0;

// Load user session on dashboard pages
if (typeof window !== 'undefined') {
    const sessionUser = localStorage.getItem('currentUser');
    if (sessionUser) {
        currentUser = JSON.parse(sessionUser);
    }
}

// Course lesson outlines
const courseLessons = {
    devops: [
        { title: "DevOps Masterclass - Lesson 1: Introduction to CI/CD", video: "https://www.youtube.com/embed/j5Zsa_eOXeU" },
        { title: "DevOps Masterclass - Lesson 2: Git Workflows and Actions", video: "https://www.youtube.com/embed/R8_veQiYBhI" },
        { title: "DevOps Masterclass - Lesson 3: Docker Containers Essentials", video: "https://www.youtube.com/embed/3c-iLjReF_A" }
    ],
    aws: [
        { title: "AWS Cloud - Lesson 1: Cloud Architecture Fundamentals", video: "https://www.youtube.com/embed/3hLmDS179YE" },
        { title: "AWS Cloud - Lesson 2: EC2 and VPC Networking Setup", video: "https://www.youtube.com/embed/Ia-UEYYR44s" }
    ],
    docker: [
        { title: "Docker & Kubernetes - Lesson 1: Containerizing Apps", video: "https://www.youtube.com/embed/fqMOX6JJhGo" },
        { title: "Docker & Kubernetes - Lesson 2: Kubernetes Cluster Architecture", video: "https://www.youtube.com/embed/X48VuDVv0do" }
    ]
};

// Course quizzes
const courseQuizzes = {
    devops: {
        question: "What is the primary difference between a Docker container and a Virtual Machine (VM)?",
        options: [
            { text: "VMs share the host OS, while containers package their own OS.", isCorrect: false },
            { text: "Containers share the host OS kernel and are lightweight, while VMs run full guest OS instances.", isCorrect: true },
            { text: "Containers are much slower to boot up than standard VMs.", isCorrect: false }
        ]
    },
    aws: {
        question: "Which AWS service is best suited for scalable, serverless object storage?",
        options: [
            { text: "Amazon EC2 (Elastic Compute Cloud)", isCorrect: false },
            { text: "Amazon EBS (Elastic Block Store)", isCorrect: false },
            { text: "Amazon S3 (Simple Storage Service)", isCorrect: true }
        ]
    },
    docker: {
        question: "What is a Kubernetes Pod?",
        options: [
            { text: "A physical server located in a cloud data center.", isCorrect: false },
            { text: "The smallest deployable unit in Kubernetes, hosting one or more containers.", isCorrect: true },
            { text: "A command-line interface tool used to build Docker images.", isCorrect: false }
        ]
    }
};

// ============================================
// Authentication & Modals (Homepage)
// ============================================
function openAuthModal(role) {
    activeRole = role;
    authMode = 'signin';
    
    // Set headers
    const titleEl = document.getElementById('authModalTitle');
    if (titleEl) {
        if (role === 'student') titleEl.textContent = 'Student Access Portal';
        else if (role === 'instructor') titleEl.textContent = 'Instructor Access Portal';
        else if (role === 'admin') titleEl.textContent = 'Admin Access Portal';
    }

    // Toggle registration tab. Hide for Admin (admin account is pre-seeded)
    const tabsContainer = document.getElementById('authTabsContainer');
    if (tabsContainer) {
        if (role === 'admin') {
            tabsContainer.style.display = 'none';
        } else {
            tabsContainer.style.display = 'flex';
        }
    }

    setAuthMode('signin');
    
    // Clear inputs
    const form = document.getElementById('authForm');
    if (form) form.reset();

    const overlay = document.getElementById('authModalOverlay');
    if (overlay) overlay.classList.add('active');
}

function closeAuthModal() {
    const overlay = document.getElementById('authModalOverlay');
    if (overlay) overlay.classList.remove('active');
}

function setAuthMode(mode) {
    authMode = mode;
    const tabSignin = document.getElementById('tabSignin');
    const tabSignup = document.getElementById('tabSignup');
    const groupName = document.getElementById('groupFullName');
    const btnSubmit = document.getElementById('authSubmitButton');

    if (mode === 'signin') {
        if (tabSignin) tabSignin.classList.add('active');
        if (tabSignup) tabSignup.classList.remove('active');
        if (groupName) groupName.style.display = 'none';
        if (btnSubmit) btnSubmit.textContent = 'Sign In';
        const nameInput = document.getElementById('regFullName');
        if (nameInput) nameInput.removeAttribute('required');
    } else {
        if (tabSignin) tabSignin.classList.remove('active');
        if (tabSignup) tabSignup.classList.add('active');
        if (groupName) groupName.style.display = 'block';
        if (btnSubmit) btnSubmit.textContent = 'Create Account';
        const nameInput = document.getElementById('regFullName');
        if (nameInput) nameInput.setAttribute('required', 'true');
    }
}

async function handleAuthSubmit(event) {
    event.preventDefault();
    
    const email = document.getElementById('authEmail').value.trim();
    const password = document.getElementById('authPassword').value.trim();
    
    if (authMode === 'signin') {
        try {
            const response = await fetch(`${API_BASE_URL}/api/auth/signin`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: email, password: password })
            });
            const data = await response.json();
            
            if (response.ok && data.success) {
                // Verify returned user matches the portal role they tried to access
                if (data.user.role !== activeRole) {
                    showToast(`Access Denied: Account is registered as ${data.user.role.toUpperCase()}`, 'error');
                    return;
                }
                
                localStorage.setItem('currentUser', JSON.stringify(data.user));
                currentUser = data.user;
                showToast(`Welcome back, ${data.user.full_name}!`, 'success');
                
                setTimeout(() => {
                    if (data.user.role === 'student') location.href = '/dashboard';
                    else if (data.user.role === 'instructor') location.href = '/instructor';
                    else if (data.user.role === 'admin') location.href = '/admin';
                }, 800);
            } else {
                showToast(data.detail || 'Incorrect credentials', 'error');
            }
        } catch (err) {
            console.error('Sign In Error:', err);
            showToast('Authentication failed', 'error');
        }
    } else {
        // Sign Up Mode
        const fullName = document.getElementById('regFullName').value.trim();
        try {
            const response = await fetch(`${API_BASE_URL}/api/auth/signup`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    full_name: fullName,
                    email: email,
                    password: password,
                    role: activeRole
                })
            });
            const data = await response.json();
            
            if (response.ok && data.success) {
                localStorage.setItem('currentUser', JSON.stringify(data.user));
                currentUser = data.user;
                showToast('Registration successful! Accessing portal...', 'success');
                
                setTimeout(() => {
                    if (data.user.role === 'student') location.href = '/dashboard';
                    else if (data.user.role === 'instructor') location.href = '/instructor';
                }, 800);
            } else {
                showToast(data.detail || 'Sign up failed', 'error');
            }
        } catch (err) {
            console.error('Sign Up Error:', err);
            showToast('Registration service offline', 'error');
        }
    }
}

// ============================================
// Homepage Job Market Preview Modal
// ============================================
async function openMarketPreview() {
    const overlay = document.getElementById('marketPreviewOverlay');
    if (overlay) overlay.classList.add('active');
    
    const container = document.getElementById('marketPreviewWidget');
    if (!container) return;
    
    container.innerHTML = '<div class="loading">Loading current market data...</div>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/market-insights?skill=developer`);
        const data = await response.json();
        
        let html = '<div style="margin-bottom:16px;"><strong>Active Technical Jobs Counted: ' + (data.total_jobs || 0) + '</strong></div>';
        if (data.skills) {
            const maxVal = Math.max(...Object.values(data.skills));
            Object.entries(data.skills).forEach(([skill, val]) => {
                const percent = maxVal > 0 ? (val / maxVal) * 100 : 0;
                html += `
                    <div class="skill-item">
                        <span class="skill-name">${skill}</span>
                        <div class="skill-bar">
                            <div class="skill-bar-fill" style="width: ${percent}%"></div>
                        </div>
                        <span class="skill-count">${val} posts</span>
                    </div>
                `;
            });
        }
        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = '<div class="loading" style="color:var(--accent-red)">Failed to load hiring trends.</div>';
    }
}

function closeMarketPreview() {
    const overlay = document.getElementById('marketPreviewOverlay');
    if (overlay) overlay.classList.remove('active');
}

// ============================================
// Student Dashboard
// ============================================
async function initializeStudentDashboard() {
    if (!currentUser) return;
    
    // Inject student name in header
    const nameDisplay = document.getElementById('studentNameDisplay');
    if (nameDisplay) {
        nameDisplay.textContent = `Student: ${currentUser.full_name}`;
    }

    loadMarketInsights();
    await loadStudentProgress(currentUser.id);
    loadDoubts(currentCourseId);
    renderActiveLesson();
    renderQuiz();
}

async function loadStudentProgress(studentId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/student/${studentId}/progress`);
        const data = await response.json();
        
        // Update progress bars
        const progressContainer = document.getElementById('progressBar');
        if (progressContainer && data.enrollments) {
            let html = '';
            data.enrollments.forEach(enrollment => {
                const progress = enrollment.progress_percent || 0;
                const title = enrollment.courses?.title || 'Course';
                html += `
                    <div class="progress-label">${title}</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                `;
            });
            
            // If the student has no enrollments display a helper message
            if (data.enrollments.length === 0) {
                html = '<div style="font-size:13px; color:var(--text-secondary);">Not enrolled in any courses yet.</div>';
            }
            progressContainer.innerHTML = html;
        }

        // Quiz score display
        const quizAvgText = document.getElementById('quizAvgText');
        if (quizAvgText) {
            quizAvgText.textContent = `${Math.round(data.average_quiz_score || 0)}%`;
        }
        
        // Trigger risk alert
        const alerts = document.querySelectorAll('.risk-banner');
        alerts.forEach(el => el.remove());
        if (data.at_risk_score > 0.6) {
            showRiskAlert();
        }
    } catch (error) {
        console.error('Error fetching progress:', error);
    }
}

function showRiskAlert() {
    const banner = document.createElement('div');
    banner.className = 'risk-banner';
    banner.style.cssText = `
        background: #ffebee;
        color: #c62828;
        padding: 14px;
        border-radius: 8px;
        margin-bottom: 20px;
        font-weight: 600;
        font-size: 14px;
        border: 1px solid #ffcdd2;
    `;
    banner.innerHTML = "[Warning] Your course engagement metric has dropped. Please review materials, attempt checkpoint quizzes, or message your tutor.";
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.insertBefore(banner, mainContent.firstChild);
    }
}

function selectCourse(courseId) {
    currentCourseId = courseId;
    activeLessonIndex = 0;
    
    // Toggle active classes in UI
    document.querySelectorAll('.course-card').forEach(el => el.classList.remove('active'));
    const activeEl = document.getElementById(`course-${courseId}`);
    if (activeEl) activeEl.classList.add('active');

    renderActiveLesson();
    renderQuiz();
    loadDoubts(courseId);
    showToast(`Switched to ${courseId.toUpperCase()} course`, 'info');
}

function renderActiveLesson() {
    const titleEl = document.getElementById('currentCourseTitle');
    const iframeEl = document.getElementById('courseVideo');
    const lessons = courseLessons[currentCourseId];
    
    if (titleEl && iframeEl && lessons && lessons[activeLessonIndex]) {
        titleEl.textContent = lessons[activeLessonIndex].title;
        iframeEl.src = lessons[activeLessonIndex].video;
    }
}

function changeLesson(direction) {
    const lessons = courseLessons[currentCourseId];
    if (!lessons) return;
    
    let newIndex = activeLessonIndex + direction;
    if (newIndex >= 0 && newIndex < lessons.length) {
        activeLessonIndex = newIndex;
        renderActiveLesson();
    } else {
        showToast("No more lessons in this module!", "info");
    }
}

function renderQuiz() {
    const qText = document.getElementById('quizQuestionText');
    const container = document.getElementById('quizContainer');
    const quiz = courseQuizzes[currentCourseId];
    
    if (qText && container && quiz) {
        qText.textContent = quiz.question;
        let html = `<h4 style="margin-bottom: 12px; font-size: 15px;" id="quizQuestionText">${quiz.question}</h4>`;
        html += '<div class="course-list" style="margin-bottom: 16px;">';
        
        quiz.options.forEach((opt, idx) => {
            html += `
                <label class="course-card" style="cursor: pointer; display: flex; align-items: center; gap: 10px;">
                    <input type="radio" name="quizOpt" value="${idx}">
                    <span>${opt.text}</span>
                </label>
            `;
        });
        
        html += '</div>';
        html += `<button class="btn-primary" style="background: var(--primary-gradient); color: white; width: 100%; font-size: 14px; padding: 10px 0;" onclick="submitActiveQuiz()">Submit Quiz Answer</button>`;
        container.innerHTML = html;
    }
}

async function submitActiveQuiz() {
    if (!currentUser) return;
    
    const selected = document.querySelector('input[name="quizOpt"]:checked');
    if (!selected) {
        showToast("Please choose an answer first!", "error");
        return;
    }
    
    const quiz = courseQuizzes[currentCourseId];
    const optionIndex = parseInt(selected.value);
    const chosenOption = quiz.options[optionIndex];
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/quiz/submit`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                student_id: currentUser.id,
                course_id: currentCourseId,
                question: quiz.question,
                answer: chosenOption.text,
                is_correct: chosenOption.isCorrect
            })
        });
        
        const data = await response.json();
        if (data.success) {
            if (chosenOption.isCorrect) {
                showToast("Correct answer! Progress updated", "success");
            } else {
                showToast("Incorrect answer! Study the lessons again.", "error");
            }
            await loadStudentProgress(currentUser.id);
        }
    } catch (error) {
        console.error('Quiz submission error:', error);
        showToast("Quiz submission failed", "error");
    }
}

// ============================================
// Market Insights
// ============================================
async function loadMarketInsights() {
    const widget = document.getElementById('marketWidget');
    if (!widget) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/market-insights?skill=developer`);
        const data = await response.json();
        
        let html = '<h3>Live Job Market Demand</h3>';
        if (data.skills) {
            const maxVal = Math.max(...Object.values(data.skills));
            Object.entries(data.skills).forEach(([skill, val]) => {
                const percent = maxVal > 0 ? (val / maxVal) * 100 : 0;
                html += `
                    <div class="skill-item">
                        <span class="skill-name">${skill}</span>
                        <div class="skill-bar">
                            <div class="skill-bar-fill" style="width: ${percent}%"></div>
                        </div>
                        <span class="skill-count">${val} jobs</span>
                    </div>
                `;
            });
        } else {
            html += '<div class="loading">No hiring data returned.</div>';
        }
        widget.innerHTML = html;
    } catch (error) {
        console.error('Market loading error:', error);
        widget.innerHTML = '<h3>Live Job Market Demand</h3><div class="loading">Data offline.</div>';
    }
}

// ============================================
// Chatbot
// ============================================
async function askQuestion() {
    if (!currentUser) return;
    const input = document.getElementById('chatInput');
    if (!input) return;
    
    const question = input.value.trim();
    if (!question) return;
    
    addMessage(question, 'user');
    input.value = '';
    
    addMessage('Tutor thinking...', 'ai', true);
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question, context: currentUser.id })
        });
        
        const data = await response.json();
        removeLoader();
        addMessage(data.answer, 'ai');
    } catch (error) {
        removeLoader();
        addMessage('Sorry, my tutor system is currently busy. Try again shortly.', 'ai');
        console.error('AI Error:', error);
    }
}

function addMessage(text, sender, isLoader = false) {
    const chatDiv = document.getElementById('chatMessages');
    if (!chatDiv) return;
    
    const msg = document.createElement('div');
    msg.className = `message ${sender}`;
    if (isLoader) msg.id = 'chatLoader';
    
    msg.innerHTML = `<div class="message-content">${escapeHtml(text)}</div>`;
    chatDiv.appendChild(msg);
    chatDiv.scrollTop = chatDiv.scrollHeight;
}

function removeLoader() {
    const loader = document.getElementById('chatLoader');
    if (loader) loader.remove();
}

// ============================================
// Doubts Forum
// ============================================
async function loadDoubts(courseId) {
    const container = document.getElementById('doubtsContainer');
    if (!container) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/doubts/${courseId}`);
        const data = await response.json();
        
        let html = '';
        if (data.doubts && data.doubts.length > 0) {
            data.doubts.forEach(doubt => {
                const author = doubt.profiles?.full_name || 'Student';
                const statusBadge = doubt.is_resolved 
                    ? '<span class="badge" style="background:#d1fae5; color:#065f46;">Resolved</span>' 
                    : '<span class="badge" style="background:#fee2e2; color:#991b1b;">Pending</span>';
                
                html += `
                    <div class="doubt-card">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <div class="doubt-question">Question: ${escapeHtml(doubt.question)}</div>
                            ${statusBadge}
                        </div>
                        <div class="doubt-meta">Asked by ${author} • ${formatDate(doubt.created_at)}</div>
                `;
                
                if (doubt.doubt_replies && doubt.doubt_replies.length > 0) {
                    html += '<div class="doubt-reply-box">';
                    doubt.doubt_replies.forEach(rep => {
                        const replier = rep.profiles?.full_name || 'Instructor';
                        html += `
                            <div class="doubt-reply-text">
                                <strong>${replier}:</strong> ${escapeHtml(rep.reply)}
                            </div>
                        `;
                    });
                    html += '</div>';
                }
                html += '</div>';
            });
        } else {
            html = '<div class="loading" style="padding: 10px 0;">No active doubts for this course. Be the first to ask!</div>';
        }
        container.innerHTML = html;
    } catch (err) {
        console.error('Error doubts:', err);
    }
}

async function postDoubt() {
    if (!currentUser) return;
    const input = document.getElementById('doubtInput');
    if (!input) return;
    
    const query = input.value.trim();
    if (!query) {
        showToast("Please enter a question to post", "error");
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/doubts`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                student_id: currentUser.id,
                course_id: currentCourseId,
                question: query
            })
        });
        
        const data = await response.json();
        if (data.success) {
            showToast("Doubt posted successfully!", "success");
            input.value = '';
            loadDoubts(currentCourseId);
        }
    } catch (error) {
        console.error('Error posting doubt:', error);
        showToast("Failed to post doubt", "error");
    }
}

// ============================================
// Instructor Dashboard
// ============================================
async function initializeInstructorDashboard() {
    if (!currentUser) return;
    
    // Inject instructor name
    const display = document.getElementById('instructorNameDisplay');
    if (display) display.textContent = `Instructor: ${currentUser.full_name}`;

    await loadAtRiskStudents();
    await loadInstructorDoubts();
}

async function loadAtRiskStudents() {
    const container = document.getElementById('atRiskTable');
    if (!container) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/instructor/${currentUser.id}/at-risk-students`);
        const data = await response.json();
        
        let html = `
            <table class="risk-table">
                <thead>
                    <tr>
                        <th>Student Name</th>
                        <th>Enrolled Course</th>
                        <th>Progress</th>
                        <th>Quiz Avg</th>
                        <th>Inactive</th>
                        <th>Risk Score</th>
                        <th>Intervene</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        if (data.at_risk_students && data.at_risk_students.length > 0) {
            const riskCountText = document.getElementById('riskCountText');
            if (riskCountText) riskCountText.textContent = data.at_risk_students.length;

            data.at_risk_students.forEach(student => {
                let riskClass = 'risk-low';
                if (student.risk_score > 75) riskClass = 'risk-high';
                else if (student.risk_score > 50) riskClass = 'risk-medium';
                
                html += `
                    <tr>
                        <td><strong>${student.student_name}</strong></td>
                        <td>${student.course_title}</td>
                        <td>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <div class="progress-bar" style="width: 80px; height:6px;">
                                    <div class="progress-fill" style="width: ${student.progress}%"></div>
                                </div>
                                <span>${student.progress}%</span>
                            </div>
                        </td>
                        <td>${student.quiz_avg}%</td>
                        <td>${student.days_inactive} days</td>
                        <td class="${riskClass}">${student.risk_score}%</td>
                        <td>
                            <button class="btn-alert" onclick="emailStudent('${student.email}', '${student.student_name}')">Email</button>
                        </td>
                    </tr>
                `;
            });
        } else {
            html += '<tr><td colspan="7" class="loading">No high-risk students flagged. Great!</td></tr>';
            const riskCountText = document.getElementById('riskCountText');
            if (riskCountText) riskCountText.textContent = '0';
        }
        
        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (err) {
        console.error('Instructor load error:', err);
    }
}

async function loadInstructorDoubts() {
    const container = document.getElementById('instructorDoubtsList');
    if (!container) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/doubts/${currentCourseId}`);
        const data = await response.json();
        
        let html = '';
        if (data.doubts && data.doubts.length > 0) {
            data.doubts.forEach(doubt => {
                const author = doubt.profiles?.full_name || 'Student';
                const statusBadge = doubt.is_resolved 
                    ? '<span class="badge" style="background:#d1fae5; color:#065f46;">Resolved</span>' 
                    : '<span class="badge" style="background:#fee2e2; color:#991b1b;">Pending Reply</span>';
                
                html += `
                    <div class="doubt-card">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <div class="doubt-question">Question: ${escapeHtml(doubt.question)}</div>
                            ${statusBadge}
                        </div>
                        <div class="doubt-meta">Asked by ${author} • ${formatDate(doubt.created_at)}</div>
                `;
                
                if (doubt.doubt_replies && doubt.doubt_replies.length > 0) {
                    html += '<div class="doubt-reply-box">';
                    doubt.doubt_replies.forEach(rep => {
                        const replier = rep.profiles?.full_name || 'Instructor';
                        html += `
                            <div class="doubt-reply-text">
                                <strong>${replier}:</strong> ${escapeHtml(rep.reply)}
                            </div>
                        `;
                    });
                    html += '</div>';
                }
                
                if (!doubt.is_resolved) {
                    html += `
                        <div style="display:flex; gap:10px; margin-top:12px;">
                            <input type="text" placeholder="Write reply..." id="replyInput-${doubt.id}" style="flex:1; padding:8px 12px; border: 1px solid var(--border-color); border-radius:6px; font-size:13px;">
                            <button class="btn-primary" style="background:var(--primary-gradient); color:white; padding:8px 16px; font-size:12px;" onclick="submitInstructorReply('${doubt.id}')">Submit Reply</button>
                        </div>
                    `;
                }
                html += '</div>';
            });
        } else {
            html = '<div class="loading">No student doubts awaiting attention for this course.</div>';
        }
        container.innerHTML = html;
    } catch (err) {
        console.error(err);
    }
}

async function submitInstructorReply(doubtId) {
    if (!currentUser) return;
    const input = document.getElementById(`replyInput-${doubtId}`);
    if (!input) return;
    
    const replyText = input.value.trim();
    if (!replyText) {
        showToast("Please enter a reply first!", "error");
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/doubts/reply`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                doubt_id: doubtId,
                user_id: currentUser.id,
                reply: replyText
            })
        });
        
        const data = await response.json();
        if (data.success) {
            showToast("Reply posted successfully!", "success");
            loadInstructorDoubts();
            loadAtRiskStudents();
        }
    } catch (error) {
        console.error('Error replying:', error);
        showToast("Failed to reply", "error");
    }
}

function selectInstructorCourse(courseId) {
    currentCourseId = courseId;
    document.querySelectorAll('.course-card').forEach(el => el.classList.remove('active'));
    const activeEl = document.getElementById(`icourse-${courseId}`);
    if (activeEl) activeEl.classList.add('active');
    
    loadInstructorDoubts();
    showToast(`Switched view to ${courseId.toUpperCase()}`, 'info');
}

function emailStudent(email, name) {
    if (email) {
        window.open(`mailto:${email}?subject=EduTrack Progress Check-in&body=Hi ${name},%0D%0A%0D%0AI noticed you haven't logged in recently or had some challenges with checkpoint quizzes. Let me know if you need any assistance!`);
    } else {
        showToast("Student email offline", "error");
    }
}

// ============================================
// Admin Dashboard
// ============================================
async function initializeAdminDashboard() {
    loadAdminMarketIntelligence();
}

async function loadAdminMarketIntelligence() {
    const container = document.getElementById('marketIntelligence');
    if (!container) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/market-intelligence`);
        const data = await response.json();
        
        let html = '<h4>Trending Skills demand (India Job Postings)</h4>';
        html += '<div style="margin-top:16px;">';
        
        if (data.trending_skills) {
            const maxCount = Math.max(...Object.values(data.trending_skills));
            Object.entries(data.trending_skills).forEach(([skill, count]) => {
                const percent = maxCount > 0 ? (count / maxCount) * 100 : 0;
                html += `
                    <div class="skill-item">
                        <span class="skill-name" style="text-transform: capitalize;">${skill}</span>
                        <div class="skill-bar">
                            <div class="skill-bar-fill" style="width: ${percent}%"></div>
                        </div>
                        <span class="skill-count">${count} listings</span>
                    </div>
                `;
            });
        } else {
            html += '<div class="loading">No listings found.</div>';
        }
        
        html += '</div>';
        container.innerHTML = html;
    } catch (err) {
        console.error('Admin market err:', err);
    }
}

function showNewBatchForm() {
    const name = prompt("Enter new Batch Name:");
    if (!name) return;
    const course = prompt("Enter Course Name:");
    if (!course) return;
    const size = prompt("Enter Max Seats:", "30");
    if (!size) return;
    
    const tableBody = document.querySelector('#batchTable tbody');
    if (tableBody) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${escapeHtml(name)}</strong></td>
            <td>${escapeHtml(course)}</td>
            <td>0/${escapeHtml(size)}</td>
            <td>${new Date().toLocaleDateString()}</td>
            <td><span style="color:var(--accent-amber);">Pending Launch</span></td>
        `;
        tableBody.appendChild(tr);
        showToast(`Batch ${name} created!`, "success");
    }
}

// ============================================
// General Helpers
// ============================================
function logout() {
    showToast("Logging out...", "info");
    localStorage.removeItem('currentUser');
    setTimeout(() => {
        location.href = '/';
    }, 1000);
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    let bg = '#6366f1';
    if (type === 'success') bg = '#10b981';
    else if (type === 'error') bg = '#ef4444';
    
    toast.style.cssText = `
        background: ${bg};
        color: white;
        min-width: 200px;
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'none';
        setTimeout(() => toast.remove(), 200);
    }, 3000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(isoString) {
    if (!isoString) return '';
    try {
        const date = new Date(isoString);
        return date.toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return isoString;
    }
}
