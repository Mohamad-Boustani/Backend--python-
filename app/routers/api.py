from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter()


def _commit_or_400(db: Session):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {exc.orig}") from exc


@router.get("/departments", response_model=list[schemas.DepartmentOut])
def list_departments(db: Session = Depends(get_db)):
    return db.query(models.Department).all()


@router.post("/departments", response_model=schemas.DepartmentOut, status_code=201)
def create_department(payload: schemas.DepartmentCreate, db: Session = Depends(get_db)):
    item = models.Department(department_name=payload.department_name)
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


@router.get("/majors", response_model=list[schemas.MajorOut])
def list_majors(db: Session = Depends(get_db)):
    return db.query(models.Major).all()


@router.post("/majors", response_model=schemas.MajorOut, status_code=201)
def create_major(payload: schemas.MajorCreate, db: Session = Depends(get_db)):
    item = models.Major(major_name=payload.major_name)
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


@router.get("/instructors", response_model=list[schemas.InstructorOut])
def list_instructors(db: Session = Depends(get_db)):
    return db.query(models.Instructor).all()


@router.post("/instructors", response_model=schemas.InstructorOut, status_code=201)
def create_instructor(payload: schemas.InstructorCreate, db: Session = Depends(get_db)):
    item = models.Instructor(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


@router.get("/students", response_model=list[schemas.StudentOut])
def list_students(db: Session = Depends(get_db)):
    return db.query(models.Student).all()


@router.post("/students", response_model=schemas.StudentOut, status_code=201)
def create_student(payload: schemas.StudentCreate, db: Session = Depends(get_db)):
    item = models.Student(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


@router.get("/admins", response_model=list[schemas.AdminOut])
def list_admins(db: Session = Depends(get_db)):
    return db.query(models.Admin).all()


@router.post("/admins", response_model=schemas.AdminOut, status_code=201)
def create_admin(payload: schemas.AdminCreate, db: Session = Depends(get_db)):
    item = models.Admin(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


@router.get("/courses", response_model=list[schemas.CourseOut])
def list_courses(db: Session = Depends(get_db)):
    return db.query(models.Course).all()


@router.post("/courses", response_model=schemas.CourseOut, status_code=201)
def create_course(payload: schemas.CourseCreate, db: Session = Depends(get_db)):
    item = models.Course(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


@router.get("/sections", response_model=list[schemas.SectionOut])
def list_sections(db: Session = Depends(get_db)):
    return db.query(models.Section).all()


@router.post("/sections", response_model=schemas.SectionOut, status_code=201)
def create_section(payload: schemas.SectionCreate, db: Session = Depends(get_db)):
    if payload.start_time >= payload.end_time:
        raise HTTPException(status_code=400, detail="Start time must be earlier than end time")

    item = models.Section(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


@router.get("/attendance-records", response_model=list[schemas.AttendanceRecordOut])
def list_attendance_records(db: Session = Depends(get_db)):
    return db.query(models.AttendanceRecord).all()


@router.post("/attendance-records", response_model=schemas.AttendanceRecordOut, status_code=201)
def create_attendance_record(payload: schemas.AttendanceRecordCreate, db: Session = Depends(get_db)):
    item = models.AttendanceRecord(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


@router.get("/face-templates", response_model=list[schemas.FaceTemplateOut])
def list_face_templates(db: Session = Depends(get_db)):
    return db.query(models.FaceTemplate).all()


@router.post("/face-templates", response_model=schemas.FaceTemplateOut, status_code=201)
def create_face_template(payload: schemas.FaceTemplateCreate, db: Session = Depends(get_db)):
    item = models.FaceTemplate(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


@router.get("/face-template-vectors", response_model=list[schemas.FaceTemplateEncodingVectorOut])
def list_face_template_vectors(db: Session = Depends(get_db)):
    return db.query(models.FaceTemplateEncodingVector).all()


@router.post("/face-template-vectors", response_model=schemas.FaceTemplateEncodingVectorOut, status_code=201)
def create_face_template_vector(payload: schemas.FaceTemplateEncodingVectorCreate, db: Session = Depends(get_db)):
    item = models.FaceTemplateEncodingVector(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item


@router.get("/enrollments", response_model=list[schemas.EnrollmentOut])
def list_enrollments(db: Session = Depends(get_db)):
    return db.query(models.Enrollment).all()


@router.post("/enrollments", response_model=schemas.EnrollmentOut, status_code=201)
def create_enrollment(payload: schemas.EnrollmentCreate, db: Session = Depends(get_db)):
    item = models.Enrollment(**payload.model_dump())
    db.add(item)
    _commit_or_400(db)
    db.refresh(item)
    return item
