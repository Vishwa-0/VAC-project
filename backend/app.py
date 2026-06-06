from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import os
import httpx
from dotenv import load_dotenv
from groq import Groq
import sys

# Fix for relative import if running directly
try:
    from .supabase_client import get_supabase_client
except ImportError:
    # Fallback for direct execution
    from supabase_client import get_supabase_client

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
print(f"[DEBUG] GROQ_API_KEY status: {'Set' if groq_key else 'Not set'}")
if groq_key and groq_key != "YOUR_GROQ_API_KEY":
    try:
        groq_client = Groq(api_key=groq_key)
        print("[INFO] Groq client initialized successfully")
        # Test the connection
        try:
            test_response = groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[{"role": "user", "content": "test"}],
                temperature=0.7,
                max_tokens=10
            )
            print("[INFO] Groq API connection test successful")
        except Exception as test_err:
            print(f"[WARNING] Groq API test failed: {test_err}. Using mock client")
            groq_client = MockGroq()
    except Exception as e:
        print(f"[WARNING] Groq client initialization failed: {e}. Falling back to Mock AI.")
        groq_client = MockGroq()
else:
    print("[WARNING] GROQ_API_KEY not found in environment. Falling back to Mock AI tutor response.")
    groq_client = MockGroq()

# ============================================
# Pydantic Models (unchanged)
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
    role: str

class SignInRequest(BaseModel):
    email: str
    password: str

# ============================================
# Helper Functions (unchanged)
# ============================================

def calculate_risk_score(enrollments, quiz_scores, last_active):
    """Simple rule-based risk score (0-1, higher = more at risk)"""
    risk = 0
    
    if enrollments:
        avg_progress = sum(e.get("progress_percent", 0) for e in enrollments) / len(enrollments)
        risk += (1 - avg_progress / 100) * 0.3
    
    if quiz_scores:
        correct_rate = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0
        risk += (1 - correct_rate) * 0.4
    
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

# ---------- Database Seeder (unchanged) ----------
def seed_database():
    """Seed the database with initial Admin, Instructor and default Courses if empty"""
    try:
        admin_res = supabase.table("profiles").select("*").eq("role", "admin").execute()
        if not admin_res.data:
            supabase.table("profiles").insert({
                "email": "admin@edutrack.com",
                "password": "adminpassword",
                "full_name": "System Administrator",
                "role": "admin"
            }).execute()
            print("[INFO] Seeded default Admin user")
        
        inst_res = supabase.table("profiles").select("*").eq("role", "instructor").execute()
        if not inst_res.data:
            supabase.table("profiles").insert({
                "email": "sharma@edutrack.com",
                "password": "instructorpassword",
                "full_name": "Prof. Sharma",
                "role": "instructor"
            }).execute()
            print("[INFO] Seeded default Instructor user")
            
        courses_res = supabase.table("courses").select("*").execute()
        if not courses_res.data:
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

@app.on_event("startup")
async def startup_event():
    seed_database()

# ============================================
# API Endpoints
# ============================================

# ---------- Groq Chat API ----------
@app.post("/api/chat")
async def chat(request: ChatRequest):
    """AI Chatbot endpoint using Groq / Mock AI"""
    try:
        print(f"[DEBUG] Chat request received: {request.question[:50]}...")
        
        system_prompt = """You are a friendly, patient tutor for a training institute. 
        Explain technical concepts in simple, easy-to-understand language. 
        Keep answers under 3 sentences. If the question is off-topic, politely redirect.
        """
        
        print("[DEBUG] Sending request to Groq...")
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
        print(f"[DEBUG] Got response: {answer[:50]}...")
        
        # Log activity to Supabase (non-blocking)
        try:
            supabase.table("activity_log").insert({
                "student_id": request.context or "anonymous",
                "activity_type": "chat_query",
                "metadata": {"question": request.question[:100], "answer": answer[:100]}
            }).execute()
        except Exception as err:
            print(f"[WARNING] Logging activity failed: {err}")
        
        return {"answer": answer, "success": True}
    except Exception as e:
        print(f"[ERROR] Chat endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# IMPORTANT: Mount static files BEFORE catch-all
# ============================================
static_dir = os.path.join(os.path.dirname(__file__), "static")

if os.path.exists(static_dir):
    print(f"[INFO] Serving static files from: {static_dir}")
    
    # Only mount static files on specific paths, not root
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # Serve index.html at root
    @app.get("/")
    async def serve_index():
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "EduTrack API is running. Static files not found."}
    
    # Catch-all for SPA routing (should be LAST)
    @app.get("/{catchall:path}")
    async def serve_frontend(catchall: str, request: Request):
        # Don't catch API routes
        if catchall.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        
        file_path = os.path.join(static_dir, catchall)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        
        raise HTTPException(status_code=404, detail="Not found")
else:
    print(f"[WARNING] Static directory not found at: {static_dir}")
    
    @app.get("/")
    async def root():
        return {"message": "EduTrack API is running", "status": "ok"}
