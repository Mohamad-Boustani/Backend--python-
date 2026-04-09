# Senior Project Backend (Python)

This backend is built from the schema in `Other Files/AI_Attendance.sql`.
It provides REST APIs that are ready for Flutter apps through JSON over HTTP.

Note: the backend is configured to use an existing database schema and does not auto-create tables on startup.

## Stack

- FastAPI (REST API)
- SQLAlchemy (ORM)
- MySQL support via PyMySQL
- Uvicorn (ASGI server)
- face_recognition for face embeddings

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

## Face Encoding

Use `POST /api/v1/face-templates/encode` with `student_id` and 3 to 4 uploaded face images. The backend will:

- detect a single face in each image
- convert each one to a 128-dimensional embedding vector using `face_recognition`
- store all vectors in the database for later matching

To identify a student during class session start, use `POST /api/v1/face-recognition/identify` with `section_id` and one live face image. The backend compares that face only against students enrolled in that section, then writes an attendance record when a match is found.

If the AI does not recognize a student, the teacher can manually submit attendance with `POST /api/v1/attendance-records/manual`. That route stores the record with a default confidence score of `1.0` because it was entered by the teacher.

## Flutter Compatibility

- CORS is enabled and configurable with `ALLOWED_ORIGINS`.
- All endpoints return JSON.
- Base API path is `/api/v1`.
