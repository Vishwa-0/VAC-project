import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Table Names
USERS_TABLE = "profiles"
COURSES_TABLE = "courses"
ENROLLMENTS_TABLE = "enrollments"
QUIZ_ATTEMPTS_TABLE = "quiz_attempts"
ACTIVITY_LOG_TABLE = "activity_log"
DOUBTS_TABLE = "doubts"
DOUBT_REPLIES_TABLE = "doubt_replies"
MARKET_INSIGHTS_TABLE = "market_insights"

# ============================================
# Mock Database and client for local fallback
# ============================================

class MockResponse:
    def __init__(self, data):
        self.data = data

class MockQuery:
    def __init__(self, table_name, client):
        self.table_name = table_name
        self.client = client
        self.filters = []
        self.order_by = None
        self.limit_val = None

    def select(self, columns):
        # We don't parse columns, we just match full objects
        return self

    def eq(self, column, value):
        self.filters.append(("eq", column, value))
        return self

    def in_(self, column, values):
        self.filters.append(("in", column, values))
        return self

    def order(self, column, desc=False):
        self.order_by = (column, desc)
        return self

    def limit(self, val):
        self.limit_val = val
        return self

    def execute(self):
        items = self.client.db.get(self.table_name, [])
        filtered_items = []
        
        for item in items:
            matches = True
            for op, col, val in self.filters:
                if op == "eq":
                    # Handle dot notation check or direct keys
                    if col not in item or item[col] != val:
                        matches = False
                        break
                elif op == "in":
                    if col not in item or item[col] not in val:
                        matches = False
                        break
            if matches:
                filtered_items.append(item.copy())

        # Sort
        if self.order_by:
            col, desc = self.order_by
            filtered_items.sort(key=lambda x: x.get(col, ""), reverse=desc)
        
        # Limit
        if self.limit_val:
            filtered_items = filtered_items[:self.limit_val]

        # Resolve relations dynamically for Mock
        for item in filtered_items:
            if self.table_name == "enrollments":
                # course relation
                course_id = item.get("course_id")
                courses = self.client.db.get("courses", [])
                item["courses"] = next((c for c in courses if c["id"] == course_id), {"title": "Unknown Course", "description": ""})
                
                # profile relation
                student_id = item.get("student_id")
                profiles = self.client.db.get("profiles", [])
                item["profiles"] = next((p for p in profiles if p["id"] == student_id), {"full_name": "Unknown Student", "email": ""})

            elif self.table_name == "doubts":
                # profile relation
                student_id = item.get("student_id")
                profiles = self.client.db.get("profiles", [])
                item["profiles"] = next((p for p in profiles if p["id"] == student_id), {"full_name": "Student"})
                
                # replies relation
                replies = self.client.db.get("doubt_replies", [])
                matched_replies = [r.copy() for r in replies if r["doubt_id"] == item["id"]]
                for r in matched_replies:
                    user_id = r.get("user_id")
                    r["profiles"] = next((p for p in profiles if p["id"] == user_id), {"full_name": "Instructor"})
                item["doubt_replies"] = matched_replies

        return MockResponse(filtered_items)

    def insert(self, data):
        if isinstance(data, list):
            inserted = []
            for row in data:
                row_copy = row.copy()
                if "id" not in row_copy:
                    row_copy["id"] = str(uuid.uuid4())
                if "created_at" not in row_copy:
                    row_copy["created_at"] = datetime.now().isoformat()
                self.client.db.setdefault(self.table_name, []).append(row_copy)
                inserted.append(row_copy)
            return MockResponse(inserted)
        else:
            row_copy = data.copy()
            if "id" not in row_copy:
                row_copy["id"] = str(uuid.uuid4())
            if "created_at" not in row_copy:
                row_copy["created_at"] = datetime.now().isoformat()
            self.client.db.setdefault(self.table_name, []).append(row_copy)
            return MockResponse([row_copy])

    def upsert(self, data):
        # In mock database, we can just insert or update if exists
        # Check if record has skill or id
        items = self.client.db.setdefault(self.table_name, [])
        key = "skill" if "skill" in data else "id"
        found = False
        for item in items:
            if item.get(key) == data.get(key):
                item.update(data)
                found = True
                break
        if not found:
            items.append(data.copy())
        return MockResponse([data])

    def update(self, data):
        items = self.client.db.get(self.table_name, [])
        updated = []
        for item in items:
            matches = True
            for op, col, val in self.filters:
                if op == "eq":
                    if item.get(col) != val:
                        matches = False
                        break
            if matches:
                item.update(data)
                updated.append(item)
        return MockResponse(updated)

class MockSupabaseClient:
    def __init__(self):
        self.db = {
            "profiles": [
                {"id": "student_123", "full_name": "Rajesh Kumar", "email": "rajesh@example.com", "role": "student"},
                {"id": "student_456", "full_name": "Priya Singh", "email": "priya@example.com", "role": "student"},
                {"id": "student_789", "full_name": "Ramesh Nair", "email": "ramesh@example.com", "role": "student"},
                {"id": "instructor_abc", "full_name": "Prof. Sharma", "email": "sharma@edutrack.com", "role": "instructor"},
                {"id": "admin_xyz", "full_name": "System Admin", "email": "admin@edutrack.com", "role": "admin"}
            ],
            "courses": [
                {"id": "devops", "title": "DevOps Masterclass", "description": "CI/CD, Docker, Kubernetes, and Cloud", "instructor_id": "instructor_abc"},
                {"id": "aws", "title": "AWS Cloud Computing", "description": "Core services, IAM, VPC, EC2, and S3", "instructor_id": "instructor_abc"},
                {"id": "docker", "title": "Docker & Kubernetes", "description": "Containers, orchestration, and deployments", "instructor_id": "instructor_abc"}
            ],
            "enrollments": [
                {"id": "e1", "student_id": "student_123", "course_id": "devops", "progress_percent": 45, "enrolled_at": "2026-05-01T10:00:00Z"},
                {"id": "e2", "student_id": "student_123", "course_id": "aws", "progress_percent": 20, "enrolled_at": "2026-05-05T12:00:00Z"},
                {"id": "e3", "student_id": "student_456", "course_id": "devops", "progress_percent": 15, "enrolled_at": "2026-05-02T11:00:00Z"},
                {"id": "e4", "student_id": "student_789", "course_id": "devops", "progress_percent": 8, "enrolled_at": "2026-05-03T09:00:00Z"}
            ],
            "quiz_attempts": [
                {"id": "q1", "student_id": "student_123", "course_id": "devops", "question": "Docker vs VM", "student_answer": "Containers share OS kernel", "is_correct": True, "attempted_at": "2026-05-10T14:00:00Z"},
                {"id": "q2", "student_id": "student_789", "course_id": "devops", "question": "Docker vs VM", "student_answer": "VMs share OS kernel", "is_correct": False, "attempted_at": "2026-05-12T16:00:00Z"}
            ],
            "activity_log": [
                {"id": "a1", "student_id": "student_123", "activity_type": "chat_query", "metadata": {"question": "What is Docker?"}, "created_at": "2026-06-04T10:00:00Z"},
                {"id": "a2", "student_id": "student_789", "activity_type": "enrollment", "metadata": {"course_id": "devops"}, "created_at": "2026-06-01T09:00:00Z"}
            ],
            "doubts": [
                {"id": "d1", "student_id": "student_123", "course_id": "devops", "question": "Why does my Docker container exit immediately?", "is_resolved": False, "created_at": "2026-06-03T11:00:00Z"},
                {"id": "d2", "student_id": "student_456", "course_id": "devops", "question": "What's the difference between CMD and ENTRYPOINT?", "is_resolved": False, "created_at": "2026-06-04T15:00:00Z"}
            ],
            "doubt_replies": [
                {"id": "r1", "doubt_id": "d2", "user_id": "instructor_abc", "reply": "CMD can be overridden, ENTRYPOINT cannot be easily overridden.", "created_at": "2026-06-04T16:00:00Z"}
            ],
            "market_insights": []
        }

    def table(self, table_name):
        return MockQuery(table_name, self)

def get_supabase_client():
    """Get Supabase client instance, falling back to local database mock if unset"""
    if not SUPABASE_URL or not SUPABASE_KEY or SUPABASE_URL == "YOUR_SUPABASE_URL":
        print("[WARNING] SUPABASE_URL/SUPABASE_KEY environment variables not found or placeholder values used.")
        print("[INFO] Falling back to the local in-memory database mock client.")
        return MockSupabaseClient()
    try:
        from supabase import create_client
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"[WARNING] Failed to connect to Supabase: {e}. Falling back to mock client.")
        return MockSupabaseClient()

# Helper function to check connection
def check_connection():
    """Test connection"""
    try:
        client = get_supabase_client()
        if isinstance(client, MockSupabaseClient):
            return {"status": "connected", "message": "Supabase mock client in-memory is operational"}
        result = client.table(USERS_TABLE).select("*").limit(1).execute()
        return {"status": "connected", "message": "Supabase cloud connection successful"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
