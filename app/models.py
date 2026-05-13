from datetime import date, datetime, time

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, DECIMAL, Enum, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# Department table for academic departments.
class Department(Base):
    __tablename__ = "departments"

    department_id: Mapped[int] = mapped_column("Department_ID", Integer, primary_key=True, index=True)
    department_name: Mapped[str] = mapped_column("Department_Name", String(50), nullable=False, unique=True)


# Instructor table for teaching staff.
class Instructor(Base):
    __tablename__ = "instructor"

    instructor_id: Mapped[int] = mapped_column("Instructor_ID", Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column("Full_Name", String(100), nullable=False)
    work_email: Mapped[str] = mapped_column("Work_Email", String(100), nullable=False, unique=True)
    department_id: Mapped[int] = mapped_column(
        "Department_ID", ForeignKey("departments.Department_ID"), nullable=False
    )

    department = relationship("Department")


# Major table for student majors.
class Major(Base):
    __tablename__ = "major"

    major_id: Mapped[int] = mapped_column("Major_ID", Integer, primary_key=True, index=True)
    major_name: Mapped[str] = mapped_column("Major_Name", String(50), nullable=False, unique=True)


# Student table for enrolled learners.
class Student(Base):
    __tablename__ = "student"

    student_id: Mapped[int] = mapped_column("Student_ID", Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column("Full_Name", String(100), nullable=False)
    university_email: Mapped[str] = mapped_column("University_Email", String(100), nullable=False, unique=True)
    phone_number: Mapped[str | None] = mapped_column("Phone_Number", String(20), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column("Archived_At", DateTime, nullable=True)
    major_id: Mapped[int] = mapped_column("Major_ID", ForeignKey("major.Major_ID"), nullable=False)

    major = relationship("Major")


# Admin table for system administrators.
class Admin(Base):
    __tablename__ = "admin"

    admin_id: Mapped[int] = mapped_column("Admin_ID", Integer, primary_key=True, index=True)
    admin_email: Mapped[str] = mapped_column("Admin_Email", String(100), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column("Full_Name", String(100), nullable=False)
    privilege_level: Mapped[str] = mapped_column("Privilege_Level", String(20), nullable=False)


# Course table for subject metadata.
class Course(Base):
    __tablename__ = "course"
    __table_args__ = (CheckConstraint("Credits > 0", name="check_course_credits_positive"),)

    course_id: Mapped[int] = mapped_column("Course_ID", Integer, primary_key=True, index=True)
    course_name: Mapped[str] = mapped_column("Course_Name", String(100), nullable=False)
    credits: Mapped[int] = mapped_column("Credits", Integer, nullable=False)
    description: Mapped[str] = mapped_column("Description", String(500), nullable=False)


# Section table for scheduled class offerings.
class Section(Base):
    __tablename__ = "section"
    __table_args__ = (CheckConstraint("Start_Time < End_Time", name="check_section_time_order"),)

    section_id: Mapped[int] = mapped_column("Section_ID", Integer, primary_key=True, index=True)
    semester: Mapped[str] = mapped_column("Semester", String(20), nullable=False)
    days: Mapped[str] = mapped_column("Days", String(20), nullable=False)
    room_number: Mapped[str] = mapped_column("Room_Number", String(20), nullable=False)
    start_time: Mapped[time] = mapped_column("Start_Time", Time, nullable=False)
    end_time: Mapped[time] = mapped_column("End_Time", Time, nullable=False)
    instructor_id: Mapped[int] = mapped_column("Instructor_ID", ForeignKey("instructor.Instructor_ID"), nullable=False)
    course_id: Mapped[int] = mapped_column("Course_ID", ForeignKey("course.Course_ID"), nullable=False)

    instructor = relationship("Instructor")
    course = relationship("Course")


# Attendance records store per-session presence and confidence.
class AttendanceRecord(Base):
    __tablename__ = "attendance_record"
    __table_args__ = (
        CheckConstraint("Confidence_Score >= 0 AND Confidence_Score <= 1", name="check_confidence_range"),
    )

    record_id: Mapped[int] = mapped_column("Record_ID", Integer, primary_key=True, index=True)
    attendance_date: Mapped[date] = mapped_column("Attendance_Date", Date, nullable=False)
    status: Mapped[str] = mapped_column(
        "Status",
        Enum("Present", "Absent", "Late", "Excused", name="attendance_status", native_enum=False),
        nullable=False,
    )
    confidence_score: Mapped[float] = mapped_column("Confidence_Score", DECIMAL(5, 4), nullable=False)
    manual_override: Mapped[bool] = mapped_column("Manual_Override", Boolean, nullable=False, default=False)
    override_reason: Mapped[str | None] = mapped_column("Override_Reason", Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column("Archived_At", DateTime, nullable=True)
    student_id: Mapped[int] = mapped_column("Student_ID", ForeignKey("student.Student_ID"), nullable=False)
    instructor_id: Mapped[int] = mapped_column("Instructor_ID", ForeignKey("instructor.Instructor_ID"), nullable=False)
    section_id: Mapped[int] = mapped_column("Section_ID", ForeignKey("section.Section_ID"), nullable=False)

    student = relationship("Student")
    instructor = relationship("Instructor")
    section = relationship("Section")


# FaceTemplate stores the owner student and last update date.
class FaceTemplate(Base):
    __tablename__ = "face_template"

    template_id: Mapped[int] = mapped_column("Template_ID", Integer, primary_key=True, index=True)
    last_updated: Mapped[date] = mapped_column("Last_Updated", Date, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column("Archived_At", DateTime, nullable=True)
    student_id: Mapped[int] = mapped_column("Student_ID", ForeignKey("student.Student_ID"), nullable=False, unique=True)

    student = relationship("Student")


# FaceTemplateEncodingVector stores the numeric face embedding as text.
class FaceTemplateEncodingVector(Base):
    __tablename__ = "face_template_encoding_vector"

    template_id: Mapped[int] = mapped_column(
        "Template_ID", ForeignKey("face_template.Template_ID"), primary_key=True
    )
    encoding_vector: Mapped[str] = mapped_column("Encoding_Vector", Text, nullable=False)

    face_template = relationship("FaceTemplate")


# Enrollment links a student to a class section.
class Enrollment(Base):
    __tablename__ = "enrollment"

    student_id: Mapped[int] = mapped_column("Student_ID", ForeignKey("student.Student_ID"), primary_key=True)
    section_id: Mapped[int] = mapped_column("Section_ID", ForeignKey("section.Section_ID"), primary_key=True)
    archived_at: Mapped[datetime | None] = mapped_column("Archived_At", DateTime, nullable=True)

    student = relationship("Student")
    section = relationship("Section")
