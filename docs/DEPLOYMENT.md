# Deployment Guide: MK-Path Analytics Platform

This guide outlines the system prerequisites, environment configuration, database setup, and production startup procedures for the MK-Path Executive Performance Management Platform.

---

## 1. Prerequisites

- **Operating System:** Windows 10/11, macOS, or Ubuntu 20.04+ LTS.
- **Python Runtime:** Python 3.10.x or 3.11.x (with `pip` and virtualenv support).
- **Node.js Runtime:** Node.js 18+ (Node 20 or 22 recommended) with `npm` 9+.
- **Database:** MongoDB Atlas cluster or local MongoDB instance (MongoDB 6.0+).
- **Storage:** Local persistent disk space for Apache Parquet fact files (`datasets/parquet/`).

---

## 2. Environment Variables Configuration

Create a `.env` file in the project root directory (`E:\MKPATH\.env`). Never commit credentials, connection strings, or API keys to Git history.

```env
# -----------------------------------------------------------------------------
# DATABASE CONFIGURATION
# -----------------------------------------------------------------------------
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-host>/mk_path?retryWrites=true&w=majority
MONGODB_DATABASE=mk_path

# -----------------------------------------------------------------------------
# APPLICATION SERVER CONFIGURATION
# -----------------------------------------------------------------------------
HOST=127.0.0.1
PORT=8000
MKPATH_MAX_UPLOAD_MB=500
MKPATH_MAX_PREVIEW_ROWS=1000

# -----------------------------------------------------------------------------
# LLM SERVICE KEYS (OPTIONAL / PLACEHOLDER NAMES ONLY)
# -----------------------------------------------------------------------------
GEMINI_API_KEY=<your_gemini_api_key_placeholder>
GEMINI_MODEL=gemini-2.5-flash-latest
GROQ_API_KEY=<your_groq_api_key_placeholder>
GROQ_MODEL=openai/gpt-oss-120b
```

---

## 3. Installation & Startup

### Step 1: Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # On Windows PowerShell
# source .venv/bin/activate    # On Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Start FastAPI application server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend API documentation will be accessible at: `http://127.0.0.1:8000/docs`.

### Step 2: Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```
The executive dashboard application will be accessible at: `http://localhost:5173`.

---

## 4. Production Build & Verification

Before deployment to staging or production environments, run automated test suites and verify the production bundle:

```bash
# 1. Run Backend Automated Test Suite
python -m pytest backend/tests/test_dashboard_analytics.py -v

# 2. Build Frontend Production Distribution
cd frontend
npm run build
```

Verify that the output generates `dist/index.html` and bundled assets with zero TypeScript compilation errors.
