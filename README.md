# AI Attendance Backend

FastAPI backend for the AI Attendance System. It exposes JSON REST endpoints for attendance, face recognition, students, enrollments, and admin management.

## Features

- Face template encoding and recognition with `face_recognition`
- Attendance capture and manual override support
- Soft-delete archive flow for students and admin-managed records
- REST API designed for the Flutter frontend

## Tech Stack

- FastAPI
- SQLAlchemy 2.x
- MySQL / MariaDB via PyMySQL
- Uvicorn
- numpy, Pillow, python-multipart

## Requirements

- Python 3.10+
- A MySQL database with the attendance schema
- `face_recognition` native dependencies installed on your machine

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file in `Backend (python)/` and set your database connection:

```env
DATABASE_URL=mysql+pymysql://user:password@host:3306/database_name
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

3. Start the API:

```bash
uvicorn app.main:app --reload
```

4. Open the interactive docs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## API Base

All routes are mounted under:

```text
/api/v1
```

## Common Workflows

### Encode face images

`POST /api/v1/face-templates/encode`

Upload 3 to 4 images for one student. The backend:

- detects a single face in each image
- converts each face to a 128-dimensional embedding
- stores the encoding vectors for later matching

### Recognize a student

`POST /api/v1/face-recognition/identify`

Send a live image plus the section ID. The backend only compares against active students enrolled in that section.

### Manual attendance

`POST /api/v1/attendance-records/manual`

Use this when the teacher records attendance directly.

## Archive Behavior

This project now uses archive-style deletes instead of hard deletes for supported records.

- Archived rows are hidden from normal list endpoints.
- Archiving a student also archives related attendance, enrollments, and face templates.
- Archiving admin setup data cascades to dependent sections, enrollments, and attendance where applicable.

## Notes

- The backend uses an existing database schema and adds missing archive columns at startup when needed.
- Make sure the Flutter frontend points to the same API base URL used by your deployment.
