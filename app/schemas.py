from datetime import date, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Request body for creating a department.
class DepartmentCreate(BaseModel):
    department_name: str = Field(min_length=1, max_length=50)


# Response model for department data.
class DepartmentOut(DepartmentCreate):
    department_id: int
    model_config = ConfigDict(from_attributes=True)


# Request body for creating a major.
class MajorCreate(BaseModel):
    major_name: str = Field(min_length=1, max_length=50)


# Response model for major data.
class MajorOut(MajorCreate):
    major_id: int
    model_config = ConfigDict(from_attributes=True)


# Request body for creating an instructor.
class InstructorCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    work_email: EmailStr
    department_id: int


# Response model for instructor data.
class InstructorOut(InstructorCreate):
    instructor_id: int
    model_config = ConfigDict(from_attributes=True)


# Request body for creating a student.
class StudentCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    university_email: EmailStr
    phone_number: str | None = Field(default=None, max_length=20)
    major_id: int


# Request body for updating a student.
class StudentUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    university_email: EmailStr | None = None
    phone_number: str | None = Field(default=None, max_length=20)
    major_id: int | None = None


# Response model for student data.
class StudentOut(StudentCreate):
    student_id: int
    model_config = ConfigDict(from_attributes=True)


# Request body for creating an admin.
class AdminCreate(BaseModel):
    admin_email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)
    privilege_level: str = Field(min_length=1, max_length=20)


# Response model for admin data.
class AdminOut(AdminCreate):
    admin_id: int
    model_config = ConfigDict(from_attributes=True)


# Request body for admin login.
class LoginRequest(BaseModel):
    admin_email: EmailStr


# Response body for admin login.
class LoginResponse(BaseModel):
    authenticated: bool
    message: str
    admin: AdminOut | None = None
    model_config = ConfigDict(from_attributes=True)


# Request body for creating a course.
class CourseCreate(BaseModel):
    course_name: str = Field(min_length=1, max_length=100)
    credits: int = Field(gt=0)
    description: str = Field(min_length=1, max_length=500)


# Response model for course data.
class CourseOut(CourseCreate):
    course_id: int
    model_config = ConfigDict(from_attributes=True)


# Request body for creating a section.
class SectionCreate(BaseModel):
    semester: str = Field(min_length=1, max_length=20)
    days: str = Field(min_length=1, max_length=20)
    room_number: str = Field(min_length=1, max_length=20)
    start_time: time
    end_time: time
    instructor_id: int
    course_id: int


# Response model for section data.
class SectionOut(SectionCreate):
    section_id: int
    model_config = ConfigDict(from_attributes=True)


# Request body for creating an attendance record.
class AttendanceRecordCreate(BaseModel):
    attendance_date: date
    status: Literal["Present", "Absent", "Late", "Excused"]
    confidence_score: Decimal = Field(ge=0, le=1)
    student_id: int
    instructor_id: int
    section_id: int


# Response model for attendance records.
class AttendanceRecordOut(AttendanceRecordCreate):
    record_id: int
    model_config = ConfigDict(from_attributes=True)


# Request body for a teacher-entered attendance record.
class AttendanceRecordManualCreate(BaseModel):
    attendance_date: date
    status: Literal["Present", "Absent", "Late", "Excused"]
    student_id: int
    instructor_id: int
    section_id: int


# Request body for saving attendance through the unified endpoint.
class AttendanceSaveCreate(BaseModel):
    attendance_date: date
    status: Literal["Present", "Absent", "Late", "Excused"]
    student_id: int
    instructor_id: int
    section_id: int
    confidence_score: Decimal | None = Field(default=None, ge=0, le=1)


# Request body for creating a face template entry.
class FaceTemplateCreate(BaseModel):
    last_updated: date
    student_id: int


# Response model for a face template.
class FaceTemplateOut(FaceTemplateCreate):
    template_id: int
    model_config = ConfigDict(from_attributes=True)


# Request body for storing a single face embedding vector.
class FaceTemplateEncodingVectorCreate(BaseModel):
    template_id: int
    encoding_vector: str


# Response model for a stored embedding vector.
class FaceTemplateEncodingVectorOut(FaceTemplateEncodingVectorCreate):
    model_config = ConfigDict(from_attributes=True)


# Response after enrolling multiple face images.
class FaceEnrollmentResponse(BaseModel):
    template_id: int
    student_id: int
    image_count: int
    encoding_vectors: list[list[float]]
    model_config = ConfigDict(from_attributes=True)


# Response after trying to identify a face during class.
class FaceRecognitionResponse(BaseModel):
    matched: bool
    student_id: int | None = None
    template_id: int | None = None
    distance: float | None = None
    section_id: int | None = None
    instructor_id: int | None = None
    attendance_record_id: int | None = None
    attendance_created: bool = False
    model_config = ConfigDict(from_attributes=True)


# Request body for enrolling a student in a section.
class EnrollmentCreate(BaseModel):
    student_id: int
    section_id: int


# Response model for enrollment records.
class EnrollmentOut(EnrollmentCreate):
    model_config = ConfigDict(from_attributes=True)


# Dashboard summary for the frontend.
class DashboardOut(BaseModel):
    total_departments: int
    total_majors: int
    total_instructors: int
    total_students: int
    total_admins: int
    total_courses: int
    total_sections: int
    total_attendance_records: int
    total_face_templates: int
    total_enrollments: int
    attendance_today: int
    present_today: int
    model_config = ConfigDict(from_attributes=True)


# Dashboard summary scoped to one instructor.
class InstructorDashboardOut(BaseModel):
    instructor_id: int
    total_students: int
    total_courses: int
    total_sections: int
    total_attendance_records: int
    attendance_today: int
    present_today: int
    model_config = ConfigDict(from_attributes=True)
