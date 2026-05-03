# Run the AI Attendance Backend (FastAPI)

This document contains copy-pasteable PowerShell commands and notes to set up and run the backend locally.

## Quick steps (PowerShell)

1) Change into the backend folder:
```powershell
cd "C:\Users\mhama\Desktop\Senior project\Backend (python)"
```

2) Create & activate a virtual environment:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3) Install Python dependencies:
```powershell
pip install -r requirements.txt
```

4) Configure environment variables:
- Copy the example and edit `.env` (the app loads it automatically):
```powershell
copy .env.example .env
notepad .env
```
- At minimum set `DATABASE_URL`. Example MySQL URL using the `senior_project` database (adjust to your credentials):

DATABASE_URL=mysql+pymysql://root:password@localhost:3306/senior_project

For quick local testing you can use SQLite instead:

DATABASE_URL=sqlite:///./ai_attendance.db

5) Create the database (if using MySQL) and create tables (SQLAlchemy models):
- Create DB manually in your MySQL client:
```sql
CREATE DATABASE ai_attendance CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```
- Create tables from the models:
```powershell
python - <<'PY'
from app.database import Base, engine
Base.metadata.create_all(bind=engine)
print("Tables created")
PY
```
(If you used SQLite the same `create_all` command will create the file and tables automatically.)

6) Start the development server with uvicorn:
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- The API root: `http://127.0.0.1:8000/`
- The versioned API prefix is `/api/v1` (e.g. `http://127.0.0.1:8000/api/v1/students`).
- `0.0.0.0` means uvicorn listens on all network interfaces so the backend is reachable from your own machine, an emulator, or another device on the same network.

## Notes and troubleshooting

- face_recognition / dlib: On Windows these packages commonly fail to build because they require C++ build tools, CMake, and sometimes specific prebuilt wheels. If you see build errors while `pip install`ing:
  - Prefer running the backend in WSL (Ubuntu) or a Linux container, where `face_recognition` installs more reliably.
  - Alternatively, avoid calling endpoints that require `face_recognition` while testing other features.

- CORS: `ALLOWED_ORIGINS` is read from the `.env`. If your frontend runs on a device or different host, set `ALLOWED_ORIGINS` in `.env` to include the frontend origin (or `*` for development).

- Database URL: `app/database.py` defaults to `mysql+pymysql://root:password@localhost:3306/ai_attendance` if `DATABASE_URL` is not set. Update `.env` to match your environment.

- Port conflicts: If `8000` is in use, change the `--port` argument when starting uvicorn.

## Quick dev-only (SQLite) example

If you just want to run the backend quickly without MySQL or face_recognition:

1) Edit `.env` and set:
```
DATABASE_URL=sqlite:///./ai_attendance.db
ALLOWED_ORIGINS=http://127.0.0.1:8080
```
2) Create tables and run (same commands as above):
```powershell
python - <<'PY'
from app.database import Base, engine
Base.metadata.create_all(bind=engine)
print("SQLite DB and tables created")
PY
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Want automation?
If you want, I can also add a PowerShell script (e.g. `setup_and_run.ps1`) in this folder that:
- Creates/activates a venv,
- Installs requirements,
- Optionally creates the SQLite DB,
- Starts uvicorn.

Tell me if you'd like that script created and whether you prefer SQLite (quick) or MySQL (production-like).
