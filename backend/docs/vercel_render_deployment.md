# FRIDAY AI — Vercel & Render Production Deployment Guide

A step-by-step production deployment manual for deploying **FRIDAY AI**:
- **Frontend**: [Vercel](https://vercel.com)
- **Backend Web Service**: [Render](https://render.com)
- **Network Protocol**: Secure HTTPS & WSS (WebSockets)

---

## 1. Architecture & Communication Overview

```mermaid
graph TD
    User([User Device - Web / Mobile])
    Vercel["Frontend (Vercel SPA)<br/>https://friday-ai.vercel.app"]
    Render["Backend (Render Web Service)<br/>https://friday-backend.onrender.com"]
    DB[("Database<br/>Render Postgres / SQLite")]
    
    User -->|HTTPS UI Load| Vercel
    Vercel -->|HTTPS REST /api/v1| Render
    Vercel -->|WSS /ws/tasks| Render
    Render -->|Async CRUD & Migrations| DB
```

---

## 2. Step-by-Step Deployment

### Part A: Backend Deployment on Render

1. **Log in to Render Dashboard**:
   - Go to [dashboard.render.com](https://dashboard.render.com).
2. **Create New Web Service**:
   - Click **New +** → **Web Service**.
   - Connect your GitHub / GitLab repository containing the `FRIDAY` project.
3. **Configure Service Settings**:
   - **Name**: `friday-backend` (or your preferred name)
   - **Region**: Closest to your users (e.g., `Singapore` / `Frankfurt` / `Oregon`)
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free` or `Starter`
4. **Configure Health Check Path**:
   - In **Advanced Settings**, set **Health Check Path** to `/api/v1/health`.
5. **Environment Variables on Render**:
   Add the following environment variables in the Render dashboard:

   | Key | Example Value | Description |
   | :--- | :--- | :--- |
   | `ENVIRONMENT` | `production` | Deployment mode |
   | `DEBUG` | `false` | Disables debug stack traces in production |
   | `TIMEZONE` | `Asia/Kolkata` | Scheduler timezone |
   | `SECRET_KEY` | *(Generate a 32+ char random string)* | JWT / PBKDF2 signing key |
   | `API_KEY` | *(Generate a secure API key)* | Secret key for authorized requests |
   | `CORS_ORIGINS` | `https://YOUR-APP.vercel.app,http://localhost:5173` | Allowed frontend origins |
   | `FRONTEND_URL` | `https://YOUR-APP.vercel.app` | Production frontend domain |
   | `DATABASE_URL` | `sqlite+aiosqlite:///./friday.db` | SQLite or Render Postgres URL |
   | `OPENAI_API_KEY` | `sk-...` *(Optional)* | For external cloud LLM reasoning |
   | `GEMINI_API_KEY` | `AIza...` *(Optional)* | For Gemini AI reasoning |

6. **Deploy**:
   - Click **Create Web Service**.
   - Note down your backend URL (e.g., `https://friday-backend.onrender.com`).

---

### Part B: Frontend Deployment on Vercel

1. **Log in to Vercel Dashboard**:
   - Go to [vercel.com/dashboard](https://vercel.com/dashboard).
2. **Import Project**:
   - Click **Add New...** → **Project**.
   - Select your Git repository.
3. **Configure Build Settings**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click **Edit** and choose `frontend`
   - **Build Command**: `npm run build` (or leave default `vite build`)
   - **Output Directory**: `dist`
4. **Environment Variables on Vercel**:
   Add the backend API base URL:

   | Key | Value | Description |
   | :--- | :--- | :--- |
   | `VITE_API_BASE_URL` | `https://friday-backend.onrender.com` | Your deployed Render backend URL |

5. **Deploy**:
   - Click **Deploy**.
   - Once deployed, copy your production Vercel domain (e.g., `https://friday-ai.vercel.app`).
6. **Update Backend CORS on Render**:
   - Return to Render → `friday-backend` → **Environment**.
   - Ensure `FRONTEND_URL` and `CORS_ORIGINS` include your exact Vercel URL.

---

## 3. Persistent Database Options on Render

### Option 1: Render Managed PostgreSQL (Recommended for Zero Maintenance)
1. In Render Dashboard, click **New +** → **PostgreSQL**.
2. Name it `friday-postgres`.
3. In your `friday-backend` web service, set `DATABASE_URL` to the Postgres **Internal Database URL** (e.g. `postgresql://user:password@hostname:5432/dbname`).
4. FRIDAY automatically translates `postgresql://` to `postgresql+asyncpg://` on startup.

### Option 2: Render Persistent Disk (For SQLite)
1. In Render Web Service settings, go to **Disks** → **Add Disk**.
2. Mount path: `/data`.
3. Set `DATABASE_URL=sqlite+aiosqlite:////data/friday.db`.

---

## 4. Post-Deployment Verification Checklist

- [ ] **Health Check**: Open `https://YOUR-BACKEND.onrender.com/api/v1/health` in browser. Expect `{"status": "healthy", "database_connected": true}`.
- [ ] **Frontend Loading**: Open `https://YOUR-APP.vercel.app`. Verify holographic UI, 3D central network, and black theme load cleanly.
- [ ] **WebSocket Stream**: Check browser DevTools Network tab for active `wss://.../ws/tasks` connection.
- [ ] **Voice Command**: Click central globe or press `Space`/`V`, speak *"Hey Friday, check the weather in Tokyo"*. Confirm task card appears in HUD and FRIDAY answers audibly.
- [ ] **Hand Gestures**: Click **ENABLE GESTURES** in the bottom HUD pill. Verify camera starts and dragging floating cards works smoothly.
