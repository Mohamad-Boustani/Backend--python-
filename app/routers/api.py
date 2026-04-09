import io
import json
from datetime import date

import face_recognition
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from fastapi import File, Form, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter()


# Convert one uploaded face image into a single 128-dimensional embedding.
def _encode_face_image(image_bytes: bytes) -> list[float]:
    image = face_recognition.load_image_file(io.BytesIO(image_bytes))
    encodings = face_recognition.face_encodings(image)

    if not encodings:
        raise HTTPException(status_code=400, detail="No face detected in the uploaded image")

    if len(encodings) > 1:
        raise HTTPException(status_code=400, detail="Multiple faces detected. Upload an image with one face only")

    return encodings[0].tolist()


# Load stored embeddings from JSON text in the database.
def _load_encoding_vectors(raw_value: str) -> list[list[float]]:
    loaded_value = json.loads(raw_value)
    if not loaded_value:
        return []
    if isinstance(loaded_value[0], (int, float)):
        return [loaded_value]
    return loaded_value


# Compare one live embedding against only the students enrolled in a section.
def _recognize_face(candidate_encoding: list[float], db: Session, section_id: int, tolerance: float = 0.6):
    candidate_array = np.asarray(candidate_encoding, dtype="float64")
    best_match = None

    enrolled_student_ids = [
        enrollment.student_id
        for enrollment in db.query(models.Enrollment).filter(models.Enrollment.section_id == section_id).all()
    ]

    if not enrolled_student_ids:
        return {"matched": False, "student_id": None, "template_id": None, "distance": None}

    for template in (
        db.query(models.FaceTemplate)
        .filter(models.FaceTemplate.student_id.in_(enrolled_student_ids))
        .all()
    ):
        template_vector = (
            db.query(models.FaceTemplateEncodingVector)
            .filter(models.FaceTemplateEncodingVector.template_id == template.template_id)
            .first()
        )
        if template_vector is None:
            continue

        stored_vectors = _load_encoding_vectors(template_vector.encoding_vector)
        if not stored_vectors:
            continue

        distances = [float(face_recognition.face_distance([stored_vector], candidate_array)[0]) for stored_vector in stored_vectors]
        current_distance = min(distances)

        if best_match is None or current_distance < best_match["distance"]:
            best_match = {
                "template_id": template.template_id,
                "student_id": template.student_id,
                "distance": current_distance,
            }

    if best_match is None:
        return {"matched": False, "student_id": None, "template_id": None, "distance": None}

    is_match = best_match["distance"] <= tolerance
    return {
        "matched": is_match,
        "student_id": best_match["student_id"] if is_match else None,
        "template_id": best_match["template_id"] if is_match else None,
        "distance": best_match["distance"],
    }


# Find the section and its instructor so attendance can be recorded.
def _get_section_context(db: Session, section_id: int):
    section = db.query(models.Section).filter(models.Section.section_id == section_id).first()
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    return section


# Prevent duplicate attendance entries for the same student, section, and date.
def _attendance_already_exists(db: Session, attendance_date: date, student_id: int, section_id: int) -> bool:
    existing_attendance = (
        db.query(models.AttendanceRecord)
        .filter(
            models.AttendanceRecord.attendance_date == attendance_date,
            models.AttendanceRecord.student_id == student_id,
            models.AttendanceRecord.section_id == section_id,
        )
        .first()
    )
    return existing_attendance is not None


def _commit_or_400(db: Session):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {exc.orig}") from exc


# List all departments.
@router.get("/departments", response_model=list[schemas.DepartmentOut])
def list_departments(db: Session = Depends(get_db)):
    return db.query(models.Department).all()


# Create a department.
@router.post("/departments", response_model=schemas.DepartmentOut, status_code=201)
def create_department(payload: schemas.DepartmentCreate, db: Session = Depends(get_db)):
    item = models.Department(department_name=payload.department_name)
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


# List all majors.
@router.get("/majors", response_model=list[schemas.MajorOut])
def list_majors(db: Session = Depends(get_db)):
    return db.query(models.Major).all()


# Create a major.
@router.post("/majors", response_model=schemas.MajorOut, status_code=201)
def create_major(payload: schemas.MajorCreate, db: Session = Depends(get_db)):
    item = models.Major(major_name=payload.major_name)
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


# List all instructors.
@router.get("/instructors", response_model=list[schemas.InstructorOut])
def list_instructors(db: Session = Depends(get_db)):
    return db.query(models.Instructor).all()


# Create an instructor.
@router.post("/instructors", response_model=schemas.InstructorOut, status_code=201)
def create_instructor(payload: schemas.InstructorCreate, db: Session = Depends(get_db)):
    item = models.Instructor(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


# List all students.
@router.get("/students", response_model=list[schemas.StudentOut])
def list_students(db: Session = Depends(get_db)):
    return db.query(models.Student).all()


# Create a student.
@router.post("/students", response_model=schemas.StudentOut, status_code=201)
def create_student(payload: schemas.StudentCreate, db: Session = Depends(get_db)):
    item = models.Student(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


# List all admins.
@router.get("/admins", response_model=list[schemas.AdminOut])
def list_admins(db: Session = Depends(get_db)):
    return db.query(models.Admin).all()


# Create an admin.
@router.post("/admins", response_model=schemas.AdminOut, status_code=201)
def create_admin(payload: schemas.AdminCreate, db: Session = Depends(get_db)):
    item = models.Admin(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


# List all courses.
@router.get("/courses", response_model=list[schemas.CourseOut])
def list_courses(db: Session = Depends(get_db)):
    return db.query(models.Course).all()


# Create a course.
@router.post("/courses", response_model=schemas.CourseOut, status_code=201)
def create_course(payload: schemas.CourseCreate, db: Session = Depends(get_db)):
    item = models.Course(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


# List all sections.
@router.get("/sections", response_model=list[schemas.SectionOut])
def list_sections(db: Session = Depends(get_db)):
    return db.query(models.Section).all()


# Create a section and validate its time order.
@router.post("/sections", response_model=schemas.SectionOut, status_code=201)
def create_section(payload: schemas.SectionCreate, db: Session = Depends(get_db)):
    if payload.start_time >= payload.end_time:
        raise HTTPException(status_code=400, detail="Start time must be earlier than end time")

    item = models.Section(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


# List attendance records.
@router.get("/attendance-records", response_model=list[schemas.AttendanceRecordOut])
def list_attendance_records(db: Session = Depends(get_db)):
    return db.query(models.AttendanceRecord).all()


# Create an attendance record.
@router.post("/attendance-records", response_model=schemas.AttendanceRecordOut, status_code=201)
def create_attendance_record(payload: schemas.AttendanceRecordCreate, db: Session = Depends(get_db)):
    if _attendance_already_exists(db, payload.attendance_date, payload.student_id, payload.section_id):
        raise HTTPException(status_code=400, detail="Attendance already exists for this student in this section on this date")

    item = models.AttendanceRecord(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


# Create an attendance record manually when the teacher overrides the AI.
@router.post("/attendance-records/manual", response_model=schemas.AttendanceRecordOut, status_code=201)
def create_manual_attendance_record(
    payload: schemas.AttendanceRecordManualCreate,
    db: Session = Depends(get_db),
):
    if _attendance_already_exists(db, payload.attendance_date, payload.student_id, payload.section_id):
        raise HTTPException(status_code=400, detail="Attendance already exists for this student in this section on this date")

    item = models.AttendanceRecord(
        **payload.model_dump(),
        confidence_score=1.0,
    )
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


# List saved face templates.
@router.get("/face-templates", response_model=list[schemas.FaceTemplateOut])
def list_face_templates(db: Session = Depends(get_db)):
    return db.query(models.FaceTemplate).all()


# Create a face template record.
@router.post("/face-templates", response_model=schemas.FaceTemplateOut, status_code=201)
def create_face_template(payload: schemas.FaceTemplateCreate, db: Session = Depends(get_db)):
    item = models.FaceTemplate(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


# List stored face embedding vectors.
@router.get("/face-template-vectors", response_model=list[schemas.FaceTemplateEncodingVectorOut])
def list_face_template_vectors(db: Session = Depends(get_db)):
    return db.query(models.FaceTemplateEncodingVector).all()


# Store a face embedding vector manually.
@router.post("/face-template-vectors", response_model=schemas.FaceTemplateEncodingVectorOut, status_code=201)
def create_face_template_vector(payload: schemas.FaceTemplateEncodingVectorCreate, db: Session = Depends(get_db)):
    item = models.FaceTemplateEncodingVector(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


# Enroll a student with 3 to 4 face images and store all embeddings.
@router.post("/face-templates/encode", response_model=schemas.FaceEnrollmentResponse, status_code=201)
async def create_face_template_encoding(
    student_id: int = Form(...),
    images: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    if len(images) < 3 or len(images) > 4:
        raise HTTPException(status_code=400, detail="Upload 3 to 4 face images for enrollment")

    encoding_vectors: list[list[float]] = []
    for image in images:
        image_bytes = await image.read()
        encoding_vectors.append(_encode_face_image(image_bytes))

    template = db.query(models.FaceTemplate).filter(models.FaceTemplate.student_id == student_id).first()
    if template is None:
        template = models.FaceTemplate(last_updated=date.today(), student_id=student_id)
        db.add(template)
        db.flush()
    else:
        template.last_updated = date.today()

    vector_json = json.dumps(encoding_vectors)
    template_vector = (
        db.query(models.FaceTemplateEncodingVector)
        .filter(models.FaceTemplateEncodingVector.template_id == template.template_id)
        .first()
    )

    if template_vector is None:
        template_vector = models.FaceTemplateEncodingVector(template_id=template.template_id, encoding_vector=vector_json)
        db.add(template_vector)
    else:
        template_vector.encoding_vector = vector_json

    _commit_or_400(db)
    db.refresh(template)
    return schemas.FaceEnrollmentResponse(
        template_id=template.template_id,
        student_id=template.student_id,
        image_count=len(encoding_vectors),
        encoding_vectors=encoding_vectors,
    )


# Identify a student within a specific section and create attendance if matched.
@router.post("/face-recognition/identify", response_model=schemas.FaceRecognitionResponse)
async def identify_face(
    section_id: int = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    section = _get_section_context(db, section_id)
    image_bytes = await image.read()
    encoding_vector = _encode_face_image(image_bytes)
    match_result = _recognize_face(encoding_vector, db, section_id)

    if not match_result["matched"] or match_result["student_id"] is None:
        return schemas.FaceRecognitionResponse(
            matched=False,
            section_id=section_id,
            instructor_id=section.instructor_id,
            attendance_created=False,
        )

    attendance = (
        db.query(models.AttendanceRecord)
        .filter(
            models.AttendanceRecord.attendance_date == date.today(),
            models.AttendanceRecord.section_id == section_id,
            models.AttendanceRecord.student_id == match_result["student_id"],
        )
        .first()
    )

    attendance_created = False
    if attendance is None:
        attendance = models.AttendanceRecord(
            attendance_date=date.today(),
            status="Present",
            confidence_score=max(0.0, min(1.0, 1.0 - float(match_result["distance"]))),
            student_id=match_result["student_id"],
            instructor_id=section.instructor_id,
            section_id=section_id,
        )
        db.add(attendance)
        _commit_or_400(db)
        db.refresh(attendance)
        attendance_created = True

    return schemas.FaceRecognitionResponse(
        matched=True,
        student_id=match_result["student_id"],
        template_id=match_result["template_id"],
        distance=match_result["distance"],
        section_id=section_id,
        instructor_id=section.instructor_id,
        attendance_record_id=attendance.record_id,
        attendance_created=attendance_created,
    )


# List student-to-section enrollments.
@router.get("/enrollments", response_model=list[schemas.EnrollmentOut])
def list_enrollments(db: Session = Depends(get_db)):
    return db.query(models.Enrollment).all()


# Create a student-to-section enrollment.
@router.post("/enrollments", response_model=schemas.EnrollmentOut, status_code=201)
def create_enrollment(payload: schemas.EnrollmentCreate, db: Session = Depends(get_db)):
    item = models.Enrollment(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item
