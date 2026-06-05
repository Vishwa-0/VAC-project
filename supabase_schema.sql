-- ============================================================
-- EduTrack - Supabase Schema
-- Run this ENTIRE script in the Supabase SQL Editor (one shot)
-- It will DROP existing tables and recreate them cleanly.
-- ============================================================


-- ========== 1. DROP TABLES (reverse dependency order) ==========

DROP TABLE IF EXISTS doubt_replies  CASCADE;
DROP TABLE IF EXISTS doubts          CASCADE;
DROP TABLE IF EXISTS quiz_attempts   CASCADE;
DROP TABLE IF EXISTS activity_log    CASCADE;
DROP TABLE IF EXISTS enrollments     CASCADE;
DROP TABLE IF EXISTS market_insights CASCADE;
DROP TABLE IF EXISTS courses         CASCADE;
DROP TABLE IF EXISTS profiles        CASCADE;


-- ========== 2. CREATE TABLES ==========

-- 2a. profiles (students, instructors, admin)
CREATE TABLE profiles (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    full_name   TEXT        NOT NULL,
    email       TEXT        NOT NULL UNIQUE,
    password    TEXT        NOT NULL,
    role        TEXT        NOT NULL CHECK (role IN ('student', 'instructor', 'admin')),
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- 2b. courses
CREATE TABLE courses (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT,
    instructor_id   UUID REFERENCES profiles(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 2c. enrollments
CREATE TABLE enrollments (
    id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id       UUID REFERENCES profiles(id) ON DELETE CASCADE,
    course_id        TEXT REFERENCES courses(id)   ON DELETE CASCADE,
    progress_percent INTEGER DEFAULT 0,
    enrolled_at      TIMESTAMPTZ DEFAULT now(),
    created_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE (student_id, course_id)
);

-- 2d. quiz_attempts
CREATE TABLE quiz_attempts (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id      UUID REFERENCES profiles(id) ON DELETE CASCADE,
    course_id       TEXT REFERENCES courses(id)   ON DELETE CASCADE,
    question        TEXT NOT NULL,
    student_answer  TEXT,
    is_correct      BOOLEAN DEFAULT false,
    attempted_at    TIMESTAMPTZ DEFAULT now(),
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 2e. activity_log
CREATE TABLE activity_log (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id      TEXT NOT NULL,
    activity_type   TEXT NOT NULL,
    metadata        JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 2f. doubts
CREATE TABLE doubts (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id  UUID REFERENCES profiles(id) ON DELETE CASCADE,
    course_id   TEXT REFERENCES courses(id)   ON DELETE CASCADE,
    question    TEXT NOT NULL,
    is_resolved BOOLEAN DEFAULT false,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- 2g. doubt_replies
CREATE TABLE doubt_replies (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    doubt_id    UUID REFERENCES doubts(id)   ON DELETE CASCADE,
    user_id     UUID REFERENCES profiles(id) ON DELETE CASCADE,
    reply       TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- 2h. market_insights (caching job data)
CREATE TABLE market_insights (
    id           UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    skill        TEXT UNIQUE NOT NULL,
    job_count    INTEGER DEFAULT 0,
    skills_data  JSONB DEFAULT '{}'::jsonb,
    last_updated TIMESTAMPTZ DEFAULT now()
);


-- ========== 3. ENABLE ROW LEVEL SECURITY ==========

ALTER TABLE profiles        ENABLE ROW LEVEL SECURITY;
ALTER TABLE courses         ENABLE ROW LEVEL SECURITY;
ALTER TABLE enrollments     ENABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_attempts   ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_log    ENABLE ROW LEVEL SECURITY;
ALTER TABLE doubts          ENABLE ROW LEVEL SECURITY;
ALTER TABLE doubt_replies   ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_insights ENABLE ROW LEVEL SECURITY;


-- ========== 4. RLS POLICIES (full CRUD via anon/service key) ==========
-- Your app uses custom auth (email+password in profiles table),
-- NOT Supabase Auth, so we allow all operations via the anon key.
-- For production, tighten these to use auth.uid() checks.

-- ---- profiles ----
CREATE POLICY "profiles_select" ON profiles FOR SELECT USING (true);
CREATE POLICY "profiles_insert" ON profiles FOR INSERT WITH CHECK (true);
CREATE POLICY "profiles_update" ON profiles FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "profiles_delete" ON profiles FOR DELETE USING (true);

-- ---- courses ----
CREATE POLICY "courses_select" ON courses FOR SELECT USING (true);
CREATE POLICY "courses_insert" ON courses FOR INSERT WITH CHECK (true);
CREATE POLICY "courses_update" ON courses FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "courses_delete" ON courses FOR DELETE USING (true);

-- ---- enrollments ----
CREATE POLICY "enrollments_select" ON enrollments FOR SELECT USING (true);
CREATE POLICY "enrollments_insert" ON enrollments FOR INSERT WITH CHECK (true);
CREATE POLICY "enrollments_update" ON enrollments FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "enrollments_delete" ON enrollments FOR DELETE USING (true);

-- ---- quiz_attempts ----
CREATE POLICY "quiz_attempts_select" ON quiz_attempts FOR SELECT USING (true);
CREATE POLICY "quiz_attempts_insert" ON quiz_attempts FOR INSERT WITH CHECK (true);
CREATE POLICY "quiz_attempts_update" ON quiz_attempts FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "quiz_attempts_delete" ON quiz_attempts FOR DELETE USING (true);

-- ---- activity_log ----
CREATE POLICY "activity_log_select" ON activity_log FOR SELECT USING (true);
CREATE POLICY "activity_log_insert" ON activity_log FOR INSERT WITH CHECK (true);
CREATE POLICY "activity_log_update" ON activity_log FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "activity_log_delete" ON activity_log FOR DELETE USING (true);

-- ---- doubts ----
CREATE POLICY "doubts_select" ON doubts FOR SELECT USING (true);
CREATE POLICY "doubts_insert" ON doubts FOR INSERT WITH CHECK (true);
CREATE POLICY "doubts_update" ON doubts FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "doubts_delete" ON doubts FOR DELETE USING (true);

-- ---- doubt_replies ----
CREATE POLICY "doubt_replies_select" ON doubt_replies FOR SELECT USING (true);
CREATE POLICY "doubt_replies_insert" ON doubt_replies FOR INSERT WITH CHECK (true);
CREATE POLICY "doubt_replies_update" ON doubt_replies FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "doubt_replies_delete" ON doubt_replies FOR DELETE USING (true);

-- ---- market_insights ----
CREATE POLICY "market_insights_select" ON market_insights FOR SELECT USING (true);
CREATE POLICY "market_insights_insert" ON market_insights FOR INSERT WITH CHECK (true);
CREATE POLICY "market_insights_update" ON market_insights FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "market_insights_delete" ON market_insights FOR DELETE USING (true);


-- ========== 5. SEED DEFAULT DATA ==========

-- 5a. Admin account (locked - only sign-in, no sign-up)
INSERT INTO profiles (full_name, email, password, role)
VALUES ('System Administrator', 'admin@edutrack.com', 'adminpassword', 'admin');

-- 5b. Default instructor
INSERT INTO profiles (full_name, email, password, role)
VALUES ('Prof. Sharma', 'sharma@edutrack.com', 'instructorpassword', 'instructor');

-- 5c. Default courses (use the instructor id we just created)
INSERT INTO courses (id, title, description, instructor_id)
VALUES
    ('devops', 'DevOps Masterclass',    'CI/CD, Docker, Kubernetes, and Cloud',         (SELECT id FROM profiles WHERE email = 'sharma@edutrack.com')),
    ('aws',    'AWS Cloud Computing',   'Core services, IAM, VPC, EC2, and S3',         (SELECT id FROM profiles WHERE email = 'sharma@edutrack.com')),
    ('docker', 'Docker & Kubernetes',   'Containers, orchestration, and deployments',    (SELECT id FROM profiles WHERE email = 'sharma@edutrack.com'));


-- ========== DONE ==========
-- Tables created: profiles, courses, enrollments, quiz_attempts,
--                 activity_log, doubts, doubt_replies, market_insights
-- RLS enabled with full CRUD policies on all tables.
-- Admin seeded:      admin@edutrack.com / adminpassword
-- Instructor seeded: sharma@edutrack.com / instructorpassword
