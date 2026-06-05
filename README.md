# EduTrack - Training Institute Platform

EduTrack is an interactive training management web platform featuring course lectures, interactive checkpoint quizzes, student doubts forum, instructor progress monitoring, admin ROI analyses, live job market demand trends, and an AI tutor chatbot.

## File Structure
```
institute-platform/
├── backend/
│   ├── app.py                 # FastAPI backend (with mock fallbacks & routing)
│   └── supabase_client.py     # Supabase client helper (with in-memory fallback)
│
├── frontend/
│   ├── index.html             # Homepage entry portal
│   ├── dashboard.html         # Student portal (Lectures, Quizzes, Doubts, Chat)
│   ├── instructor.html        # Instructor dashboard (At-risk students, doubt answering)
│   ├── admin.html             # Admin panel (ROI audit, market demand listings)
│   ├── styles.css             # Unified CSS styles
│   └── script.js              # State synchronizer & client logic
│
├── requirements.txt           # Python dependency declarations
├── render.yaml                # Render service blueprint
├── .gitignore                 # Standard file exclusions
└── README.md                  # Project instructions
```

## Resilience Out-of-the-Box (Mocks)
This project is engineered to work immediately upon booting up:
* **No Database Configuration Required:** If `SUPABASE_URL` and `SUPABASE_KEY` are not set in your environment, the platform automatically starts an in-memory mock client preloaded with mockup students, profiles, grades, and doubts which you can query, update, and resolve!
* **No AI Key Required:** If `GROQ_API_KEY` is not present, the chatbot uses a local matching dictionary to answer student programming and DevOps inquiries.
* **No Offline CSS Styling Issues:** Static paths are resolved cleanly via FastAPI root mounting fallbacks to prevent unstyled text page loads.

## Installation & Running Locally

1. **Clone the Repository:**
   ```bash
   git clone <your-repository-url>
   cd institute-platform
   ```

2. **Create a Virtual Environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the Development Server:**
   ```bash
   python -m backend.app
   ```
   or
   ```bash
   uvicorn backend.app:app --reload
   ```

5. **Access the platform:**
   Open `http://localhost:8000` in your web browser.

## Hosting on Render
To deploy to Render:
1. Push this project folder to your GitHub account.
2. In the Render Dashboard, click **New +** > **Blueprint**.
3. Select this GitHub repository.
4. Render will read `render.yaml` and configure the service automatically. Add your `SUPABASE_URL`, `SUPABASE_KEY`, and `GROQ_API_KEY` environment variables in the Render console under the service's Environment settings if you'd like to link live databases and APIs.
