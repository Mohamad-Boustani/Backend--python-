# Railway Deployment Guide

This backend is ready to deploy on Railway.

## Prerequisites

- Railway account at https://railway.app
- GitHub repository with this code pushed

## Deployment Steps

1. **Push code to GitHub:**
   - Make sure `.venv`, `.env`, and `__pycache__/` are in `.gitignore` (already done).
   - Push the `Backend (python)` folder to your GitHub repo.

2. **Create a new Railway project:**
   - Go to https://railway.app and create a new project.
   - Select "Deploy from GitHub" and choose your repository.
   - If your repository contains multiple apps (for example Flutter + backend), set Railway service **Root Directory** to `Backend (python)`.
   - Railway will auto-detect `Procfile`, `railpack.json`, and `requirements.txt` from that root directory.

3. **Add MySQL Database:**
   - In Railway, add a MySQL plugin to your project.
   - Railway will auto-generate a `DATABASE_URL` connection string.

4. **Set environment variables:**
   - Go to Railway project → Variables tab.
   - Add these variables (Railway provides `DATABASE_URL` automatically):
     - `APP_NAME=AI Attendance Backend`
     - `ALLOWED_ORIGINS=*` (or set specific frontend URL in production)

5. **Deploy:**
   - Railway will automatically build and deploy when you push to GitHub.
   - Your API will be live at: `https://<your-railway-domain>/api/v1/...`

## How it works

- **Procfile**: Tells Railway how to start the app (`uvicorn app.main:app`).
- **requirements.txt**: Python dependencies are installed automatically.
- **DATABASE_URL**: Railway MySQL plugin provides the connection string.
- **.env**: Not needed; use Railway's variable system instead.

## Notes

- Railway auto-scales and manages the server.
- Logs are viewable in the Railway dashboard.
- The backend will use the `$PORT` environment variable that Railway provides.
- Keep `.venv`, `.env`, and `__pycache__/` out of Git (see `.gitignore`).

## Troubleshooting

If the build fails:
- Check Railway build logs for missing dependencies.
- Ensure `requirements.txt` has all packages (including `face-recognition` if needed; see note below).
- Verify `app/main.py` imports are correct.

**Note on `face-recognition`:**
- If `face-recognition` fails to build on Railway, you may need to deploy in a Docker container or use a Python image with build tools pre-installed.
- Railway supports custom Dockerfile deployments; contact Railway support if needed.
