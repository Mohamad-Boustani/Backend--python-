from datetime import date, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class DepartmentCreate(BaseModel):
    department_name: str = Field(min_length=1, max_length=50)


class DepartmentOut(DepartmentCreate):
    department_id: int
    model_config = ConfigDict(from_attributes=True)


class MajorCreate(BaseModel):
    major_name: str = Field(min_length=1, max_length=50)


class MajorOut(MajorCreate):
    major_id: int
    model_config = ConfigDict(from_attributes=True)


class InstructorCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    work_email: EmailStr
    department_id: int


class InstructorOut(InstructorCreate):
    instructor_id: int
    model_config = ConfigDict(from_attributes=True)


class StudentCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    university_email: EmailStr
    phone_number: str | None = Field(default=None, max_length=20)
    major_id: int


class StudentOut(StudentCreate):
    student_id: int
    model_config = ConfigDict(from_attributes=True)


class AdminCreate(BaseModel):
    admin_email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)
    privilege_level: str = Field(min_length=1, max_length=20)


class AdminOut(AdminCreate):
    admin_id: int
    model_config = ConfigDict(from_attributes=True)


class CourseCreate(BaseModel):
    course_name: str = Field(min_length=1, max_length=100)
    credits: int = Field(gt=0)
    description: str = Field(min_length=1, max_length=500)


class CourseOut(CourseCreate):
    course_id: int
    model_config = ConfigDict(from_attributes=True)


class SectionCreate(BaseModel):
    semester: str = Field(min_length=1, max_length=20)
    days: str = Field(min_length=1, max_length=20)
    room_number: str = Field(min_length=1, max_length=20)
    start_time: time
    end_time: time
    instructor_id: int
    course_id: int


class SectionOut(SectionCreate):
    section_id: int
    model_config = ConfigDict(from_attributes=True)


class AttendanceRecordCreate(BaseModel):
    attendance_date: date
    status: Literal["Present", "Absent", "Late", "Excused"]
    confidence_score: Decimal = Field(ge=0, le=1)
    student_id: int
    instructor_id: int
    section_id: int


class AttendanceRecordOut(AttendanceRecordCreate):
    record_id: int
    model_config = ConfigDict(from_attributes=True)


class FaceTemplateCreate(BaseModel):
    last_updated: date
    student_id: int


class FaceTemplateOut(FaceTemplateCreate):
    template_id: int
    model_config = ConfigDict(from_attributes=True)


class FaceTemplateEncodingVectorCreate(BaseModel):
    template_id: int
    encoding_vector: str


class FaceTemplateEncodingVectorOut(FaceTemplateEncodingVectorCreate):
    model_config = ConfigDict(from_attributes=True)


class EnrollmentCreate(BaseModel):
    student_id: int
    section_id: int


class EnrollmentOut(EnrollmentCreate):
    model_config = ConfigDict(from_attributes=True)
