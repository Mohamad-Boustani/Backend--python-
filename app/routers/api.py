import io
import json
from datetime import date

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import File, Form, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter()


def _get_face_recognition():
    try:
        import face_recognition
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Face recognition is unavailable in this deployment",
        ) from exc

    return face_recognition


# Convert one uploaded face image into a single 128-dimensional embedding.
def _encode_face_image(image_bytes: bytes) -> list[float]:
    face_recognition = _get_face_recognition()
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
    face_recognition = _get_face_recognition()
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


# Find a student by primary key so update and delete can share the same 404 behavior.
def _get_student_context(db: Session, student_id: int):
    student = db.query(models.Student).filter(models.Student.student_id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


# Find the first admin profile when no authentication system is available.
def _get_admin_profile(db: Session):
    admin = db.query(models.Admin).order_by(models.Admin.admin_id.asc()).first()
    if admin is None:
        raise HTTPException(status_code=404, detail="Admin not found")
    return admin


# Validate the student, section, and enrollment required for attendance writes.
def _validate_attendance_targets(db: Session, student_id: int, section_id: int):
    student = db.query(models.Student).filter(models.Student.student_id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    section = _get_section_context(db, section_id)
    enrollment_exists = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.student_id == student_id,
            models.Enrollment.section_id == section_id,
        )
        .first()
        is not None
    )
    if not enrollment_exists:
        raise HTTPException(status_code=400, detail="Student is not enrolled in this section")

    return student, section


# Prevent deleting a student who is still referenced by other tables.
def _student_has_dependencies(db: Session, student_id: int) -> list[str]:
    dependencies: list[str] = []

    if db.query(models.Enrollment).filter(models.Enrollment.student_id == student_id).first() is not None:
        dependencies.append("enrollments")

    if db.query(models.AttendanceRecord).filter(models.AttendanceRecord.student_id == student_id).first() is not None:
        dependencies.append("attendance records")

    if db.query(models.FaceTemplate).filter(models.FaceTemplate.student_id == student_id).first() is not None:
        dependencies.append("face templates")

    return dependencies


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


# Return a count for a table query without loading rows.
def _count_rows(query) -> int:
    return int(query.count())


# Ensure a student email stays unique when updating records.
def _student_email_in_use(db: Session, university_email: str, student_id: int | None = None) -> bool:
    query = db.query(models.Student).filter(models.Student.university_email == university_email)
    if student_id is not None:
        query = query.filter(models.Student.student_id != student_id)
    return query.first() is not None


# Ensure a major exists before assigning it to a student.
def _major_exists(db: Session, major_id: int) -> bool:
    return db.query(models.Major).filter(models.Major.major_id == major_id).first() is not None


# Log in an admin by email because the current schema does not store passwords.
@router.post("/auth/login", response_model=schemas.LoginResponse)
def login_admin(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter(models.Admin.admin_email == payload.admin_email).first()
    if admin is None:
        raise HTTPException(status_code=401, detail="Invalid admin email")

    return schemas.LoginResponse(
        authenticated=True,
        message="Login successful",
        admin=admin,
    )


# Return a lightweight summary for the admin dashboard.
@router.get("/dashboard", response_model=schemas.DashboardOut)
def get_dashboard_summary(db: Session = Depends(get_db)):
    today = date.today()

    total_attendance_records = db.query(models.AttendanceRecord).count()
    attendance_today = db.query(models.AttendanceRecord).filter(models.AttendanceRecord.attendance_date == today).count()
    present_today = (
        db.query(models.AttendanceRecord)
        .filter(
            models.AttendanceRecord.attendance_date == today,
            models.AttendanceRecord.status == "Present",
        )
        .count()
    )

    return schemas.DashboardOut(
        total_departments=_count_rows(db.query(models.Department)),
        total_majors=_count_rows(db.query(models.Major)),
        total_instructors=_count_rows(db.query(models.Instructor)),
        total_students=_count_rows(db.query(models.Student)),
        total_admins=_count_rows(db.query(models.Admin)),
        total_courses=_count_rows(db.query(models.Course)),
        total_sections=_count_rows(db.query(models.Section)),
        total_attendance_records=total_attendance_records,
        total_face_templates=_count_rows(db.query(models.FaceTemplate)),
        total_enrollments=_count_rows(db.query(models.Enrollment)),
        attendance_today=attendance_today,
        present_today=present_today,
    )


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


# Search students by name.
@router.get("/students/search", response_model=list[schemas.StudentOut])
def search_students(name: str, db: Session = Depends(get_db)):
    return (
        db.query(models.Student)
        .filter(models.Student.full_name.ilike(f"%{name}%"))
        .all()
    )


# Create a student.
@router.post("/students", response_model=schemas.StudentOut, status_code=201)
def create_student(payload: schemas.StudentCreate, db: Session = Depends(get_db)):
    item = models.Student(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


# Update an existing student.
@router.put("/students/{student_id}", response_model=schemas.StudentOut)
def update_student(student_id: int, payload: schemas.StudentUpdate, db: Session = Depends(get_db)):
    student = _get_student_context(db, student_id)
    update_data = payload.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="At least one field must be provided")

    if "university_email" in update_data and _student_email_in_use(db, update_data["university_email"], student_id):
        raise HTTPException(status_code=400, detail="University email already exists")

    if "major_id" in update_data and not _major_exists(db, update_data["major_id"]):
        raise HTTPException(status_code=404, detail="Major not found")

    for field_name, field_value in update_data.items():
        setattr(student, field_name, field_value)

    _commit_or_400(db)
    db.refresh(student)
    return student


# Delete a student.
@router.delete("/students/{student_id}", response_model=schemas.StudentOut)
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = _get_student_context(db, student_id)

    dependencies = _student_has_dependencies(db, student_id)
    if dependencies:
        dependency_list = ", ".join(dependencies)
        raise HTTPException(
            status_code=409,
            detail=f"Student cannot be deleted because related {dependency_list} still exist",
        )

    db.delete(student)
    _commit_or_400(db)
    return student


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


# List students enrolled in one section.
@router.get("/sections/{section_id}/students", response_model=list[schemas.StudentOut])
def list_section_students(section_id: int, db: Session = Depends(get_db)):
    _get_section_context(db, section_id)
    return (
        db.query(models.Student)
        .join(models.Enrollment, models.Student.student_id == models.Enrollment.student_id)
        .filter(models.Enrollment.section_id == section_id)
        .order_by(models.Student.full_name.asc())
        .all()
    )


# List attendance records.
@router.get("/attendance-records", response_model=list[schemas.AttendanceRecordOut])
def list_attendance_records(db: Session = Depends(get_db)):
    return db.query(models.AttendanceRecord).all()


# Create an attendance record.
@router.post("/attendance-records", response_model=schemas.AttendanceRecordOut, status_code=201)
def create_attendance_record(payload: schemas.AttendanceRecordCreate, db: Session = Depends(get_db)):
    _validate_attendance_targets(db, payload.student_id, payload.section_id)

    if _attendance_already_exists(db, payload.attendance_date, payload.student_id, payload.section_id):
        raise HTTPException(status_code=400, detail="Attendance already exists for this student in this section on this date")

    item = models.AttendanceRecord(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


# Save attendance through the unified endpoint used by auto and manual flows.
@router.post("/attendance", response_model=schemas.AttendanceRecordOut, status_code=201)
def save_attendance(payload: schemas.AttendanceSaveCreate, db: Session = Depends(get_db)):
    _validate_attendance_targets(db, payload.student_id, payload.section_id)

    if _attendance_already_exists(db, payload.attendance_date, payload.student_id, payload.section_id):
        raise HTTPException(status_code=400, detail="Attendance already exists for this student in this section on this date")

    attendance_data = payload.model_dump(exclude_none=True)
    confidence_score = float(attendance_data.pop("confidence_score", 1.0))
    item = models.AttendanceRecord(**attendance_data, confidence_score=confidence_score)
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


# Get attendance records for a single section and date.
@router.get("/attendance", response_model=list[schemas.AttendanceRecordOut])
def get_attendance_for_class(
    section_id: int = Query(...),
    attendance_date: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
):
    _get_section_context(db, section_id)

    return (
        db.query(models.AttendanceRecord)
        .filter(
            models.AttendanceRecord.section_id == section_id,
            models.AttendanceRecord.attendance_date == attendance_date,
        )
        .order_by(models.AttendanceRecord.record_id.asc())
        .all()
    )


# Get attendance history for one section.
@router.get("/attendance/history", response_model=list[schemas.AttendanceRecordOut])
def get_attendance_history(section_id: int, db: Session = Depends(get_db)):
    _get_section_context(db, section_id)
    return (
        db.query(models.AttendanceRecord)
        .filter(models.AttendanceRecord.section_id == section_id)
        .order_by(models.AttendanceRecord.attendance_date.desc(), models.AttendanceRecord.record_id.desc())
        .all()
    )


# Search attendance history by student name.
@router.get("/attendance/history/search", response_model=list[schemas.AttendanceRecordOut])
def search_attendance_history(name: str, section_id: int | None = None, db: Session = Depends(get_db)):
    query = (
        db.query(models.AttendanceRecord)
        .join(models.Student, models.Student.student_id == models.AttendanceRecord.student_id)
        .filter(models.Student.full_name.ilike(f"%{name}%"))
    )
    if section_id is not None:
        query = query.filter(models.AttendanceRecord.section_id == section_id)
    return query.order_by(models.AttendanceRecord.attendance_date.desc(), models.AttendanceRecord.record_id.desc()).all()


# Create an attendance record manually when the teacher overrides the AI.
@router.post("/attendance-records/manual", response_model=schemas.AttendanceRecordOut, status_code=201)
def create_manual_attendance_record(
    payload: schemas.AttendanceRecordManualCreate,
    db: Session = Depends(get_db),
):
    _validate_attendance_targets(db, payload.student_id, payload.section_id)

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


# Register one face image for a student.
@router.post("/face/register", response_model=schemas.FaceEnrollmentResponse, status_code=201)
async def register_face(
    student_id: int = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    image_bytes = await image.read()
    encoding_vector = _encode_face_image(image_bytes)

    template = db.query(models.FaceTemplate).filter(models.FaceTemplate.student_id == student_id).first()
    if template is None:
        template = models.FaceTemplate(last_updated=date.today(), student_id=student_id)
        db.add(template)
        db.flush()
    else:
        template.last_updated = date.today()

    vector_json = json.dumps([encoding_vector])
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
        image_count=1,
        encoding_vectors=[encoding_vector],
    )


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
@router.post("/face/recognize", response_model=schemas.FaceRecognitionResponse)
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


# Return the current admin profile.
@router.get("/admin/profile", response_model=schemas.AdminOut)
def get_admin_profile(db: Session = Depends(get_db)):
    return _get_admin_profile(db)


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
