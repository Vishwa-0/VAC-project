from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
import httpx
from dotenv import load_dotenv
from groq import Groq
from .supabase_client import get_supabase_client

load_dotenv()

# Initialize FastAPI
app = FastAPI(title="EduTrack API", description="Training Institute Platform")

# CORS Middleware (Fixed for Render and Local Testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your Render URL
    allow_credentials=False,  # Fixed: Cannot be True when allow_origins is ["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
supabase = get_supabase_client()

# ============================================
# Groq Client Initialization & Mock Fallback
# ============================================
class MockChatCompletions:
    def create(self, model, messages, temperature, max_tokens):
        question = messages[-1]["content"].lower()
        if "docker" in question:
            answer = "Docker is a tool that containerizes applications. Containers package an application with all its requirements, sharing the host OS kernel. This makes them lightweight and fast to boot."
        elif "kubernetes" in question or "k8s" in question:
            answer = "Kubernetes is an open-source orchestration tool that manages containers. It handles auto-scaling, deployments, load balancing, and organizes containers into logical groups called Pods."
        elif "ci/cd" in question:
            answer = "CI/CD stands for Continuous Integration and Continuous Deployment. It automates testing, integration, and delivery of code commits to production, ensuring frequent and safe releases."
        elif "risk" in question or "score" in question:
            answer = "The risk score measures a student's engagement. It weights quiz scores (40%), progress percent (30%), and days inactive (30%) to flag students needing academic assistance."
        else:
            answer = "That is a great question! As your EduTrack AI tutor, I suggest checking our course sections on Docker, Kubernetes, and AWS. Let me know what specific part I can clarify!"
        
        class MockChoice:
            class MockMessage:
                def __init__(self, content):
                    self.content = content
            def __init__(self, content):
                self.message = MockChoice.MockMessage(content)
                
        class MockResponse:
            def __init__(self, content):
                self.choices = [MockChoice(content)]
                
        return MockResponse(answer)

class MockGroq:
    def __init__(self, api_key=None):
        self.chat = type('MockChat', (), {'completions': MockChatCompletions()})()

groq_key = os.getenv("GROQ_API_KEY")
if groq_key and groq_key != "YOUR_GROQ_API_KEY":
    try:
        groq_client = Groq(api_key=groq_key)
    except Exception as e:
        print(f"[WARNING] Groq client initialization failed: {e}. Falling back to Mock AI.")
        groq_client = MockGroq()
else:
    print("[WARNING] GROQ_API_KEY not found in environment. Falling back to Mock AI tutor response.")
    groq_client = MockGroq()

# ============================================
# Pydantic Models
# ============================================

class ChatRequest(BaseModel):
    question: str
    context: Optional[str] = None

class StudentProgress(BaseModel):
    student_id: str
    course_id: str

class EnrollmentRequest(BaseModel):
    student_id: str
    course_id: str

class QuizAttempt(BaseModel):
    student_id: str
    course_id: str
    question: str
    answer: str
    is_correct: bool

class DoubtRequest(BaseModel):
    student_id: str
    course_id: str
    question: str

class DoubtReply(BaseModel):
    doubt_id: str
    user_id: str
    reply: str

class SignUpRequest(BaseModel):
    full_name: str
    email: str
    password: str
    role: str  # student or instructor

class SignInRequest(BaseModel):
    email: str
    password: str

# ============================================
# Helper Functions
# ============================================

def calculate_risk_score(enrollments, quiz_scores, last_active):
    """Simple rule-based risk score (0-1, higher = more at risk)"""
    risk = 0
    
    # Factor 1: Progress (30% weight)
    if enrollments:
        avg_progress = sum(e.get("progress_percent", 0) for e in enrollments) / len(enrollments)
        risk += (1 - avg_progress / 100) * 0.3
    
    # Factor 2: Quiz performance (40% weight)
    if quiz_scores:
        correct_rate = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0
        risk += (1 - correct_rate) * 0.4
    
    # Factor 3: Last activity (30% weight)
    if last_active:
        try:
            if isinstance(last_active, str):
                last_active_clean = last_active.replace('Z', '+00:00')
                days_inactive = (datetime.now() - datetime.fromisoformat(last_active_clean)).days
            else:
                days_inactive = 0
        except Exception:
            days_inactive = 0
        risk += min(days_inactive / 14, 1) * 0.3
    
    return min(risk, 1.0)

# ---------- Database Seeder ----------
def seed_database():
    """Seed the database with initial Admin, Instructor and default Courses if empty"""
    try:
        # Check if Admin exists
        admin_res = supabase.table("profiles").select("*").eq("role", "admin").execute()
        if not admin_res.data:
            supabase.table("profiles").insert({
                "email": "admin@edutrack.com",
                "password": "adminpassword",
                "full_name": "System Administrator",
                "role": "admin"
            }).execute()
            print("[INFO] Seeded default Admin user in profiles: admin@edutrack.com / adminpassword")
        
        # Check if default Instructor exists
        inst_res = supabase.table("profiles").select("*").eq("role", "instructor").execute()
        if not inst_res.data:
            supabase.table("profiles").insert({
                "email": "sharma@edutrack.com",
                "password": "instructorpassword",
                "full_name": "Prof. Sharma",
                "role": "instructor"
            }).execute()
            print("[INFO] Seeded default Instructor user in profiles: sharma@edutrack.com / instructorpassword")
            
        # Seed default Courses if empty
        courses_res = supabase.table("courses").select("*").execute()
        if not courses_res.data:
            # Find the instructor id
            i_res = supabase.table("profiles").select("*").eq("role", "instructor").execute()
            inst_id = i_res.data[0]["id"] if i_res.data else "instructor_abc"
            
            supabase.table("courses").insert([
                {"id": "devops", "title": "DevOps Masterclass", "description": "CI/CD, Docker, Kubernetes, and Cloud", "instructor_id": inst_id},
                {"id": "aws", "title": "AWS Cloud Computing", "description": "Core services, IAM, VPC, EC2, and S3", "instructor_id": inst_id},
                {"id": "docker", "title": "Docker & Kubernetes", "description": "Containers, orchestration, and deployments", "instructor_id": inst_id}
            ]).execute()
            print("[INFO] Seeded default courses")
    except Exception as e:
        print(f"[WARNING] Database seeding check skipped or failed: {e}")

# Run seed function on startup
@app.on_event("startup")
async def startup_event():
    seed_database()

# ============================================
# API Endpoints
# ============================================

# ---------- Authentication ----------
@app.post("/api/auth/signup")
def signup(request: SignUpRequest):
    """Register a new student in the database"""
    if request.role != "student":
        raise HTTPException(status_code=400, detail="Registration is only allowed for students.")
    
    try:
        # Check if email is already taken
        user_res = supabase.table("profiles").select("*").eq("email", request.email).execute()
        if user_res.data:
            raise HTTPException(status_code=400, detail="User with this email already exists.")
        
        new_user = {
            "email": request.email,
            "password": request.password,
            "full_name": request.full_name,
            "role": request.role
        }
        
        insert_res = supabase.table("profiles").insert(new_user).execute()
        if not insert_res.data:
            raise HTTPException(status_code=500, detail="Failed to create user account.")
            
        user_data = insert_res.data[0]
        
        # If student, auto-enroll in DevOps Masterclass
        if request.role == "student":
            try:
                supabase.table("enrollments").insert({
                    "student_id": user_data["id"],
                    "course_id": "devops",
                    "progress_percent": 0,
                    "enrolled_at": datetime.now().isoformat()
                }).execute()
            except Exception as enroll_err:
                print(f"[WARNING] Automatic course enrollment failed: {enroll_err}")
                
        return {
            "success": True, 
            "user": {
                "id": user_data["id"], 
                "full_name": user_data["full_name"], 
                "role": user_data["role"]
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        err_msg = str(e)
        if "password" in err_msg.lower():
            raise HTTPException(status_code=500, detail="Database Schema Error: Please ensure your 'profiles' table has a 'password' column (text).")
        raise HTTPException(status_code=500, detail=f"Registration failed: {err_msg}")

@app.post("/api/auth/signin")
def signin(request: SignInRequest):
    """Authenticate student, instructor, or admin credentials"""
    try:
        user_res = supabase.table("profiles")\
            .select("*")\
            .eq("email", request.email)\
            .eq("password", request.password)\
            .execute()
            
        if not user_res.data:
            raise HTTPException(status_code=401, detail="Invalid email or password.")
            
        user_data = user_res.data[0]
        return {
            "success": True, 
            "user": {
                "id": user_data["id"], 
                "full_name": user_data["full_name"], 
                "role": user_data["role"]
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        err_msg = str(e)
        if "password" in err_msg.lower():
            raise HTTPException(status_code=500, detail="Database Schema Error: Please ensure your 'profiles' table has a 'password' column (text).")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {err_msg}")


# ---------- Health Check ----------
@app.get("/api/root")
def api_root():
    return {
        "status": "running",
        "api": "EduTrack API",
        "version": "1.1.0",
        "endpoints": [
            "/api/auth/signup",
            "/api/auth/signin",
            "/api/chat",
            "/api/market-insights",
            "/api/student/{id}/progress",
            "/api/enroll",
            "/api/quiz/submit",
            "/api/doubts/{course_id}",
            "/api/instructor/{id}/at-risk-students",
            "/api/admin/market-intelligence"
        ]
    }


# ---------- Groq Chat API ----------
@app.post("/api/chat")
def chat(request: ChatRequest):
    """AI Chatbot endpoint using Groq / Mock AI"""
    try:
        system_prompt = """You are a friendly, patient tutor for a training institute. 
        Explain technical concepts in simple, easy-to-understand language. 
        Keep answers under 3 sentences. If the question is off-topic, politely redirect.
        """
        
        response = groq_client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.question}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        answer = response.choices[0].message.content
        
        # Log activity to Supabase
        try:
            supabase.table("activity_log").insert({
                "student_id": request.context or "anonymous",
                "activity_type": "chat_query",
                "metadata": {"question": request.question[:100], "answer": answer[:100]}
            }).execute()
        except Exception as err:
            print(f"Logging activity failed: {err}")
        
        return {"answer": answer, "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Himalayas Market Insights ----------
@app.get("/api/market-insights")
def market_insights(skill: str = None):
    """Get live job market data from Himalayas API with fallback to cached mock data"""
    query = skill if skill else "developer"
    try:
        with httpx.Client() as client:
            response = client.get(
                "https://himalayas.app/jobs/api/search",
                params={
                    "country": "in",
                    "query": query,
                    "sort": "recent",
                    "limit": 20
                },
                timeout=10.0
            )
            
            data = response.json()
            jobs = data.get("jobs", [])
            
            skills_count = {
                "Python": 0, "AWS": 0, "Docker": 0, 
                "Kubernetes": 0, "React": 0, "Java": 0,
                "JavaScript": 0, "DevOps": 0
            }
            
            for job in jobs:
                desc = job.get("description", "").lower()
                for skill_name in skills_count.keys():
                    if skill_name.lower() in desc:
                        skills_count[skill_name] += 1
            
            # Cache in Supabase
            try:
                supabase.table("market_insights").upsert({
                    "skill": query,
                    "job_count": len(jobs),
                    "skills_data": skills_count,
                    "last_updated": datetime.now().isoformat()
                }).execute()
            except Exception as err:
                print(f"Caching market insights failed: {err}")
            
            return {
                "total_jobs": len(jobs),
                "skills": skills_count,
                "sample_jobs": jobs[:5],
                "source": "Himalayas API"
            }
    except Exception as e:
        print(f"Himalayas API Error: {e}. Returning mock data.")
        mock_skills = {
            "Python": 14, "AWS": 10, "Docker": 12, 
            "Kubernetes": 8, "React": 15, "Java": 9,
            "JavaScript": 18, "DevOps": 11
        }
        return {
            "total_jobs": 25,
            "skills": mock_skills,
            "sample_jobs": [],
            "source": "EduTrack Mock Cache"
        }


# ---------- Student Progress ----------
@app.get("/api/student/{student_id}/progress")
def get_student_progress(student_id: str):
    """Get student's progress across all courses"""
    try:
        # Get enrollments with progress
        enrollments = supabase.table("enrollments")\
            .select("*, courses(title, description)")\
            .eq("student_id", student_id)\
            .execute()
        
        # Get quiz performance
        quizzes = supabase.table("quiz_attempts")\
            .select("*")\
            .eq("student_id", student_id)\
            .execute()
        
        # Calculate average quiz score
        quiz_scores = [1 if q.get("is_correct") else 0 for q in quizzes.data]
        avg_score = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0
        
        # Get last activity
        activities = supabase.table("activity_log")\
            .select("*")\
            .eq("student_id", student_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        last_active = activities.data[0].get("created_at") if activities.data else None
        
        return {
            "enrollments": enrollments.data,
            "average_quiz_score": avg_score * 100,
            "total_quizzes": len(quiz_scores),
            "last_active": last_active,
            "at_risk_score": calculate_risk_score(enrollments.data, quiz_scores, last_active)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Enroll in Course ----------
@app.post("/api/enroll")
def enroll_student(request: EnrollmentRequest):
    """Enroll a student in a course"""
    try:
        enrollment = supabase.table("enrollments").insert({
            "student_id": request.student_id,
            "course_id": request.course_id,
            "progress_percent": 0,
            "enrolled_at": datetime.now().isoformat()
        }).execute()
        
        # Log activity
        supabase.table("activity_log").insert({
            "student_id": request.student_id,
            "activity_type": "enrollment",
            "metadata": {"course_id": request.course_id}
        }).execute()
        
        return {"success": True, "enrollment": enrollment.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Submit Quiz ----------
@app.post("/api/quiz/submit")
def submit_quiz(attempt: QuizAttempt):
    """Record a quiz attempt"""
    try:
        result = supabase.table("quiz_attempts").insert({
            "student_id": attempt.student_id,
            "course_id": attempt.course_id,
            "question": attempt.question,
            "student_answer": attempt.answer,
            "is_correct": attempt.is_correct,
            "attempted_at": datetime.now().isoformat()
        }).execute()
        
        # Update enrollment progress (simple logic)
        enrollment = supabase.table("enrollments")\
            .select("*")\
            .eq("student_id", attempt.student_id)\
            .eq("course_id", attempt.course_id)\
            .execute()
        
        if enrollment.data:
            current_progress = enrollment.data[0].get("progress_percent", 0)
            new_progress = min(current_progress + 5, 100)
            supabase.table("enrollments")\
                .update({"progress_percent": new_progress})\
                .eq("student_id", attempt.student_id)\
                .eq("course_id", attempt.course_id)\
                .execute()
        
        # Log activity
        supabase.table("activity_log").insert({
            "student_id": attempt.student_id,
            "activity_type": "quiz_complete",
            "metadata": {"course_id": attempt.course_id, "correct": attempt.is_correct}
        }).execute()
        
        return {"success": True, "message": "Quiz recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Doubts Forum ----------
@app.get("/api/doubts/{course_id}")
def get_doubts(course_id: str):
    """Get all doubts for a course"""
    try:
        doubts = supabase.table("doubts")\
            .select("*, profiles(full_name), doubt_replies(*, profiles(full_name))")\
            .eq("course_id", course_id)\
            .order("created_at", desc=True)\
            .execute()
        return {"doubts": doubts.data}
    except Exception as e:
        return {"doubts": []}

@app.post("/api/doubts")
def create_doubt(request: DoubtRequest):
    """Create a new doubt"""
    try:
        doubt = supabase.table("doubts").insert({
            "student_id": request.student_id,
            "course_id": request.course_id,
            "question": request.question,
            "created_at": datetime.now().isoformat()
        }).execute()
        return {"success": True, "doubt": doubt.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/doubts/reply")
def reply_to_doubt(request: DoubtReply):
    """Reply to a doubt"""
    try:
        reply = supabase.table("doubt_replies").insert({
            "doubt_id": request.doubt_id,
            "user_id": request.user_id,
            "reply": request.reply,
            "created_at": datetime.now().isoformat()
        }).execute()
        
        # Mark doubt as resolved
        supabase.table("doubts").update({"is_resolved": True}).eq("id", request.doubt_id).execute()
        
        return {"success": True, "reply": reply.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- At-Risk Students (Instructor Dashboard) ----------
@app.get("/api/instructor/{instructor_id}/at-risk-students")
def get_at_risk_students(instructor_id: str):
    """Get students at risk of dropping out"""
    try:
        # Get courses taught by instructor
        courses = supabase.table("courses")\
            .select("id, title")\
            .eq("instructor_id", instructor_id)\
            .execute()
        
        course_ids = [c["id"] for c in courses.data] if courses.data else []
        
        if not course_ids:
            return {"at_risk_students": []}
        
        # Get enrollments for those courses
        enrollments = supabase.table("enrollments")\
            .select("*, profiles(full_name, email), courses(title)")\
            .in_("course_id", course_ids)\
            .execute()
        
        # Calculate risk for each student
        at_risk = []
        for enrollment in enrollments.data:
            student_id = enrollment.get("student_id")
            
            # Get quiz performance
            quizzes = supabase.table("quiz_attempts")\
                .select("*")\
                .eq("student_id", student_id)\
                .execute()
            
            quiz_scores = [1 if q.get("is_correct") else 0 for q in quizzes.data]
            avg_score = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0
            
            # Get last activity
            activities = supabase.table("activity_log")\
                .select("*")\
                .eq("student_id", student_id)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            last_active = activities.data[0].get("created_at") if activities.data else None
            
            risk_score = calculate_risk_score(
                [enrollment], 
                quiz_scores, 
                last_active
            )
            
            days_inactive = 0
            if last_active:
                try:
                    last_active_clean = last_active.replace('Z', '+00:00')
                    days_inactive = (datetime.now() - datetime.fromisoformat(last_active_clean)).days
                except Exception:
                    days_inactive = 0
            
            at_risk.append({
                "student_id": student_id,
                "student_name": enrollment.get("profiles", {}).get("full_name", "Unknown"),
                "email": enrollment.get("profiles", {}).get("email", ""),
                "course_title": enrollment.get("courses", {}).get("title", ""),
                "progress": enrollment.get("progress_percent", 0),
                "quiz_avg": round(avg_score * 100, 1),
                "days_inactive": days_inactive,
                "risk_score": round(risk_score * 100, 1)
            })
        
        at_risk.sort(key=lambda x: x["risk_score"], reverse=True)
        return {"at_risk_students": at_risk[:20]}
    except Exception as e:
        return {"at_risk_students": []}


# ---------- Instructor Dashboard: Quiz Analytics ----------
@app.get("/api/instructor/{instructor_id}/quiz-analytics")
def get_quiz_analytics(instructor_id: str):
    """Aggregate quiz success rates for the instructor's courses"""
    try:
        courses = supabase.table("courses").select("id").eq("instructor_id", instructor_id).execute()
        course_ids = [c["id"] for c in courses.data] if courses.data else []
        
        if not course_ids:
            return {"quiz_analytics": []}
            
        attempts = supabase.table("quiz_attempts")\
            .select("question, is_correct")\
            .in_("course_id", course_ids)\
            .execute()
            
        question_stats = {}
        for attempt in (attempts.data or []):
            q = attempt.get("question")
            is_correct = attempt.get("is_correct", False)
            if q not in question_stats:
                question_stats[q] = {"total": 0, "correct": 0}
            question_stats[q]["total"] += 1
            if is_correct:
                question_stats[q]["correct"] += 1
                
        analytics = []
        for q, stats in question_stats.items():
            success_rate = round((stats["correct"] / stats["total"]) * 100) if stats["total"] > 0 else 0
            analytics.append({
                "question": q,
                "total_attempts": stats["total"],
                "correct_attempts": stats["correct"],
                "success_rate": success_rate
            })
            
        return {"quiz_analytics": analytics}
    except Exception as e:
        return {"quiz_analytics": []}


# ---------- Instructor Dashboard: Engagement Heatmap ----------
@app.get("/api/instructor/{instructor_id}/engagement-heatmap")
def get_engagement_heatmap(instructor_id: str):
    """Calculate weekly student activities for the past 4 weeks"""
    try:
        courses = supabase.table("courses").select("id").eq("instructor_id", instructor_id).execute()
        course_ids = [c["id"] for c in courses.data] if courses.data else []
        
        if not course_ids:
            return {"heatmap_data": []}
            
        # Get all enrollments for these courses
        enrollments = supabase.table("enrollments")\
            .select("student_id, profiles(full_name)")\
            .in_("course_id", course_ids)\
            .execute()
            
        student_map = {}
        for e in (enrollments.data or []):
            sid = e.get("student_id")
            sname = e.get("profiles", {}).get("full_name") if e.get("profiles") else "Unknown Student"
            student_map[sid] = sname
            
        if not student_map:
            return {"heatmap_data": []}
            
        # Get activity logs for these students
        logs = supabase.table("activity_log")\
            .select("student_id, created_at")\
            .in_("student_id", list(student_map.keys()))\
            .execute()
            
        # Group activity by student and week
        now = datetime.now()
        heatmap_data = []
        
        for sid, name in student_map.items():
            s_logs = [l for l in (logs.data or []) if l.get("student_id") == sid]
            
            # Count activities per week
            weekly_counts = [0, 0, 0, 0]
            for log in s_logs:
                try:
                    created_at_clean = log.get("created_at").replace('Z', '+00:00')
                    dt = datetime.fromisoformat(created_at_clean)
                    days_ago = (now - dt).days
                    if 0 <= days_ago < 7:
                        weekly_counts[0] += 1
                    elif 7 <= days_ago < 14:
                        weekly_counts[1] += 1
                    elif 14 <= days_ago < 21:
                        weekly_counts[2] += 1
                    elif 21 <= days_ago < 28:
                        weekly_counts[3] += 1
                except Exception:
                    pass
            
            weekly_status = []
            for count in weekly_counts:
                if count >= 3:
                    weekly_status.append("active")
                elif count > 0:
                    weekly_status.append("warning")
                else:
                    weekly_status.append("inactive")
                    
            weekly_status.reverse()
            
            heatmap_data.append({
                "student_name": name,
                "weeks": weekly_status
            })
            
        return {"heatmap_data": heatmap_data}
    except Exception as e:
        return {"heatmap_data": []}


# ---------- Instructor Dashboard: Repetitive Queries ----------
@app.get("/api/instructor/{instructor_id}/repetitive-queries")
def get_repetitive_queries(instructor_id: str):
    """Analyze student chat queries and forum doubts to find repetitive issues"""
    try:
        courses = supabase.table("courses").select("id").eq("instructor_id", instructor_id).execute()
        course_ids = [c["id"] for c in courses.data] if courses.data else []
        
        if not course_ids:
            return {"repetitive_queries": []}
            
        # Get all doubts
        doubts = supabase.table("doubts")\
            .select("question, created_at")\
            .in_("course_id", course_ids)\
            .execute()
            
        # Get all chat queries from activity log
        chat_logs = supabase.table("activity_log")\
            .select("metadata, created_at")\
            .eq("activity_type", "chat_query")\
            .execute()
            
        all_texts = []
        for d in (doubts.data or []):
            all_texts.append(d.get("question", "").lower())
        for cl in (chat_logs.data or []):
            meta = cl.get("metadata") or {}
            all_texts.append(meta.get("question", "").lower())
            
        keywords = ["docker", "kubernetes", "pod", "aws", "s3", "cicd", "permission", "port", "error", "connection", "yaml", "cmd", "entrypoint", "volume", "container"]
        keyword_counts = {kw: 0 for kw in keywords}
        
        for text in all_texts:
            for kw in keywords:
                if kw in text:
                    keyword_counts[kw] += 1
                    
        sorted_kws = [{"keyword": k, "count": c} for k, c in keyword_counts.items() if c > 0]
        sorted_kws.sort(key=lambda x: x["count"], reverse=True)
        
        recent_doubts = doubts.data[:5] if doubts.data else []
        
        return {
            "keyword_frequencies": sorted_kws,
            "sample_doubts": recent_doubts,
            "total_queries": len(all_texts)
        }
    except Exception as e:
        return {"keyword_frequencies": [], "sample_doubts": [], "total_queries": 0}


# ---------- Student Dashboard: Available Courses ----------
@app.get("/api/courses/available")
def get_available_courses(student_id: str):
    """Get all courses the student is NOT currently enrolled in"""
    try:
        # Get all courses
        all_courses = supabase.table("courses").select("*, profiles(full_name)").execute()
        
        # Get student's enrollments
        enrollments = supabase.table("enrollments")\
            .select("course_id")\
            .eq("student_id", student_id)\
            .execute()
            
        enrolled_ids = [e["course_id"] for e in enrollments.data] if enrollments.data else []
        
        # Filter out courses the student is already enrolled in
        available_courses = [
            course for course in (all_courses.data or [])
            if course.get("id") not in enrolled_ids
        ]
        
        return {"available_courses": available_courses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Serve Frontend Static Files
# ============================================
static_dir = os.path.join(os.path.dirname(__file__), "static")

if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    @app.get("/{catchall:path}")
    def serve_frontend(request: Request):
        return FileResponse(os.path.join(static_dir, "index.html"))
