# Senior Project Backend (Python)

This backend is built from the schema in `Other Files/AI_Attendance.sql`.
It provides REST APIs that are ready for Flutter apps through JSON over HTTP.

Note: the backend is configured to use an existing database schema and does not auto-create tables on startup.

## Stack

- FastAPI (REST API)
- SQLAlchemy (ORM)
- MySQL support via PyMySQL
- Uvicorn (ASGI server)

## Quick Start

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create `.env` from `.env.example` and update `DATABASE_URL`.

3. Run the API:

```bash
uvicorn app.main:app --reload
```

4. Open docs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Flutter Compatibility

- CORS is enabled and configurable with `ALLOWED_ORIGINS`.
- All endpoints return JSON.
- Base API path is `/api/v1`.
