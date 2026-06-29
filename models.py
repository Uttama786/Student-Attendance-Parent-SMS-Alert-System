"""
models.py — SQLAlchemy ORM models for the attendance system.

Tables:
  Faculty    — system users (admin / faculty roles)
  Student    — student records with parent contact info
  Attendance — per-subject per-day attendance entries
  SMSLog     — audit trail of every SMS sent via Twilio
"""
from datetime import datetime, date
import enum

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db, login_manager


# ─────────────────────────────── Enums ───────────────────────────────────────

class AttendanceStatus(enum.Enum):
    PRESENT = "Present"
    ABSENT = "Absent"


class SMSDeliveryStatus(enum.Enum):
    SENT = "Sent"
    FAILED = "Failed"
    PENDING = "Pending"


# ─────────────────────────────── Models ──────────────────────────────────────

class Faculty(UserMixin, db.Model):
    """
    Represents a faculty member / admin who can log in and mark attendance.
    role: 'admin' or 'faculty'
    """
    __tablename__ = "faculty"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="faculty")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    attendance_records = db.relationship("Attendance", backref="faculty", lazy="dynamic")

    def set_password(self, password: str) -> None:
        """Hash and store a plain-text password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify a plain-text password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def __repr__(self) -> str:
        return f"<Faculty {self.username} ({self.role})>"


class Student(db.Model):
    """
    Stores student profile and parent contact information.
    student_id is the college-issued roll/registration number (unique string).
    """
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(30), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    parent_name = db.Column(db.String(120), nullable=False)
    parent_phone = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    attendance_records = db.relationship(
        "Attendance", backref="student", lazy="dynamic", cascade="all, delete-orphan"
    )
    sms_logs = db.relationship(
        "SMSLog", backref="student", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Student {self.student_id} — {self.name}>"


class Attendance(db.Model):
    """
    Records a single student's attendance for a specific subject and date.
    A composite unique constraint prevents duplicate entries.
    """
    __tablename__ = "attendance"
    __table_args__ = (
        db.UniqueConstraint("student_id", "subject", "date", name="uq_attendance_entry"),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=True)
    subject = db.Column(db.String(120), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.PRESENT)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Attendance student={self.student_id} {self.subject} {self.date} {self.status.value}>"


class SMSLog(db.Model):
    """
    Audit log for every SMS attempt made via Twilio.
    Stores the full message text and Twilio's delivery status.
    """
    __tablename__ = "sms_log"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    parent_phone = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_time = db.Column(db.DateTime, default=datetime.utcnow)
    delivery_status = db.Column(
        db.Enum(SMSDeliveryStatus),
        nullable=False,
        default=SMSDeliveryStatus.PENDING,
    )
    twilio_sid = db.Column(db.String(64), nullable=True)  # Twilio message SID for tracking
    error_message = db.Column(db.Text, nullable=True)  # Detailed error description if failed

    def __repr__(self) -> str:
        return f"<SMSLog to={self.parent_phone} status={self.delivery_status.value}>"


class Subject(db.Model):
    """
    Represents a subject in the system, mapped to a specific semester.
    """
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    semester = db.Column(db.Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<Subject {self.name} (Semester {self.semester})>"


# ─────────────────────────── Flask-Login callback ────────────────────────────

@login_manager.user_loader
def load_user(user_id: str):
    """Load a Faculty instance by primary key for Flask-Login."""
    return db.session.get(Faculty, int(user_id))
