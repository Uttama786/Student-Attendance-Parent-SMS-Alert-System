"""
blueprints/attendance/routes.py — Attendance marking and history.

Routes:
  GET  /attendance/mark         — Subject/date selector + student list
  POST /attendance/mark         — Save attendance, trigger SMS for absences
  GET  /attendance/history      — Filterable attendance history table
  GET  /attendance/sms-log      — SMS audit log
"""
from datetime import date, datetime

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify,
)
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length, NumberRange

from extensions import db
from models import Student, Attendance, SMSLog, AttendanceStatus, Subject
from blueprints.sms.service import send_absence_sms

attendance_bp = Blueprint("attendance", __name__, template_folder="../../templates/attendance")

# ─────────────────────────────── Forms ───────────────────────────────────────

class AttendanceForm(FlaskForm):
    subject = SelectField(
        "Subject",
        choices=[],
        validators=[DataRequired(message="Please select a subject")],
    )
    attendance_date = DateField(
        "Date",
        validators=[DataRequired()],
        default=date.today,
    )


class SubjectForm(FlaskForm):
    name = StringField(
        "Subject Name",
        validators=[DataRequired(message="Subject name is required"), Length(max=120)],
    )
    semester = IntegerField(
        "Semester",
        validators=[
            DataRequired(message="Semester is required"),
            NumberRange(min=1, max=8, message="Semester must be between 1 and 8"),
        ],
    )


# ─────────────────────────────── Routes ──────────────────────────────────────

@attendance_bp.route("/mark", methods=["GET", "POST"])
@login_required
def mark():
    """
    Step 1 (GET):  Faculty selects subject + date → sees student list.
    Step 2 (POST): Faculty submits Present/Absent for each student.
                   Absent students trigger an SMS to their parent.
    """
    form = AttendanceForm()
    db_subjects = Subject.query.order_by(Subject.name).all()
    form.subject.choices = [("", "— Select Subject —")] + [(s.name, s.name) for s in db_subjects]

    # On initial GET without query params, show the selector form
    subject = request.args.get("subject") or request.form.get("subject", "")
    date_str = request.args.get("date") or request.form.get("attendance_date", str(date.today()))
    semester_str = request.args.get("semester") or request.form.get("semester", "")

    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        selected_date = date.today()

    students = []
    existing_map = {}  # student_id -> AttendanceStatus

    if subject:
        # Load students (filtered by semester if specified)
        q = Student.query
        if semester_str:
            try:
                q = q.filter(Student.semester == int(semester_str))
            except ValueError:
                pass
        students = q.order_by(Student.name).all()

        # Load already-marked entries for this subject/date
        existing = Attendance.query.filter_by(
            subject=subject, date=selected_date
        ).all()
        existing_map = {e.student_id: e.status for e in existing}

    if request.method == "POST" and subject and students:
        sms_count = 0
        saved = 0
        date_display = selected_date.strftime("%A, %d %B %Y")

        for student in students:
            field_name = f"status_{student.id}"
            status_value = request.form.get(field_name, "Present")
            status = (
                AttendanceStatus.PRESENT
                if status_value == "Present"
                else AttendanceStatus.ABSENT
            )

            # Upsert: update if already exists, else insert
            record = Attendance.query.filter_by(
                student_id=student.id,
                subject=subject,
                date=selected_date,
            ).first()

            if record:
                record.status = status
                record.faculty_id = current_user.id
            else:
                record = Attendance(
                    student_id=student.id,
                    faculty_id=current_user.id,
                    subject=subject,
                    date=selected_date,
                    status=status,
                )
                db.session.add(record)

            # Send SMS only for absent students
            if status == AttendanceStatus.ABSENT:
                try:
                    log_entry = send_absence_sms(student, subject, date_display)
                    if log_entry.delivery_status.value == "Sent":
                        sms_count += 1
                    else:
                        flash(f"SMS alert failed for {student.name}: {log_entry.error_message}", "warning")
                except Exception as exc:
                    flash(f"SMS failed for {student.name}: {exc}", "warning")

            saved += 1

        db.session.commit()
        flash(
            f"Attendance saved for {saved} students. "
            f"{sms_count} SMS notification(s) sent successfully.",
            "success",
        )
        return redirect(url_for("attendance.mark", subject=subject, date=date_str, semester=semester_str))

    return render_template(
        "attendance/mark.html",
        title="Mark Attendance",
        form=form,
        subjects=db_subjects,
        students=students,
        selected_subject=subject,
        selected_date=selected_date,
        selected_semester=semester_str,
        existing_map=existing_map,
        AttendanceStatus=AttendanceStatus,
    )


@attendance_bp.route("/history")
@login_required
def history():
    """View filterable attendance history."""
    subject_filter = request.args.get("subject", "")
    date_filter = request.args.get("date", "")
    student_filter = request.args.get("student_id", "")
    page = request.args.get("page", 1, type=int)

    q = (
        db.session.query(Attendance, Student)
        .join(Student, Attendance.student_id == Student.id)
    )

    if subject_filter:
        q = q.filter(Attendance.subject == subject_filter)
    if date_filter:
        try:
            d = datetime.strptime(date_filter, "%Y-%m-%d").date()
            q = q.filter(Attendance.date == d)
        except ValueError:
            pass
    if student_filter:
        q = q.filter(
            Student.name.ilike(f"%{student_filter}%")
            | Student.student_id.ilike(f"%{student_filter}%")
        )

    records = q.order_by(Attendance.date.desc(), Student.name).paginate(
        page=page, per_page=20, error_out=False
    )

    db_subjects = [s.name for s in Subject.query.order_by(Subject.name).all()]

    return render_template(
        "attendance/history.html",
        title="Attendance History",
        records=records,
        subjects=db_subjects,
        subject_filter=subject_filter,
        date_filter=date_filter,
        student_filter=student_filter,
        AttendanceStatus=AttendanceStatus,
    )


@attendance_bp.route("/sms-log")
@login_required
def sms_log():
    """View SMS audit log."""
    page = request.args.get("page", 1, type=int)
    logs = (
        db.session.query(SMSLog, Student)
        .join(Student, SMSLog.student_id == Student.id)
        .order_by(SMSLog.sent_time.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )
    return render_template(
        "attendance/sms_log.html",
        title="SMS Log",
        logs=logs,
    )


@attendance_bp.route("/subjects", methods=["GET", "POST"])
@login_required
def subjects_list():
    """List and add subjects."""
    form = SubjectForm()
    if form.validate_on_submit():
        name = form.name.data.strip().upper()
        semester = form.semester.data

        # Duplicate subject check
        existing = Subject.query.filter_by(name=name).first()
        if existing:
            flash(f"Subject '{name}' already exists.", "danger")
        else:
            sub = Subject(name=name, semester=semester)
            db.session.add(sub)
            db.session.commit()
            flash(f"Subject '{name}' added successfully for Semester {semester}.", "success")
            return redirect(url_for("attendance.subjects_list"))

    subjects = Subject.query.order_by(Subject.semester, Subject.name).all()
    return render_template(
        "attendance/subjects.html",
        title="Subject Management",
        subjects=subjects,
        form=form,
    )


@attendance_bp.route("/subjects/<int:subject_id>/delete", methods=["POST"])
@login_required
def delete_subject(subject_id: int):
    """Delete a subject."""
    sub = Subject.query.get_or_404(subject_id)
    name = sub.name
    db.session.delete(sub)
    db.session.commit()
    flash(f"Subject '{name}' deleted.", "warning")
    return redirect(url_for("attendance.subjects_list"))
