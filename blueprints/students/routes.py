"""
blueprints/students/routes.py — Student CRUD management.

Routes:
  GET  /students/           — Paginated list with search
  GET  /students/add        — Add student form
  POST /students/add        — Create student
  GET  /students/<id>/edit  — Edit student form
  POST /students/<id>/edit  — Update student
  POST /students/<id>/delete — Delete student
"""
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, abort,
)
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField
from wtforms.validators import DataRequired, Length, NumberRange, Regexp

from extensions import db
from models import Student

students_bp = Blueprint("students", __name__, template_folder="../../templates/students")

DEPARTMENTS = [
    "AIML",
]


# ─────────────────────────────── Forms ───────────────────────────────────────

class StudentForm(FlaskForm):
    student_id = StringField(
        "Student ID / Roll No.",
        validators=[DataRequired(), Length(max=30)],
    )
    name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    department = SelectField(
        "Department",
        choices=[(d, d) for d in DEPARTMENTS],
        validators=[DataRequired()],
    )
    semester = IntegerField(
        "Semester",
        validators=[DataRequired(), NumberRange(min=1, max=12)],
    )
    parent_name = StringField("Parent / Guardian Name", validators=[DataRequired(), Length(max=120)])
    parent_phone = StringField(
        "Parent Phone (with country code, e.g. +91XXXXXXXXXX)",
        validators=[
            DataRequired(),
            Length(min=7, max=20),
            Regexp(r"^\+?[0-9\s\-()]+$", message="Enter a valid phone number"),
        ],
    )


# ─────────────────────────────── Routes ──────────────────────────────────────

@students_bp.route("/")
@login_required
def list_students():
    """Display paginated & searchable student list."""
    query = request.args.get("q", "").strip()
    dept_filter = request.args.get("dept", "").strip()
    page = request.args.get("page", 1, type=int)

    q = Student.query
    if query:
        q = q.filter(
            Student.name.ilike(f"%{query}%") | Student.student_id.ilike(f"%{query}%")
        )
    if dept_filter:
        q = q.filter_by(department=dept_filter)

    students = q.order_by(Student.name).paginate(page=page, per_page=15, error_out=False)

    return render_template(
        "students/list.html",
        title="Students",
        students=students,
        query=query,
        dept_filter=dept_filter,
        departments=DEPARTMENTS,
    )


@students_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_student():
    """Add a new student."""
    form = StudentForm()

    if form.validate_on_submit():
        # Check for duplicate student ID
        existing = Student.query.filter_by(student_id=form.student_id.data.strip()).first()
        if existing:
            flash(f"Student ID '{form.student_id.data}' already exists.", "danger")
            return render_template("students/form.html", form=form, title="Add Student", action="add")

        student = Student(
            student_id=form.student_id.data.strip(),
            name=form.name.data.strip(),
            department=form.department.data,
            semester=form.semester.data,
            parent_name=form.parent_name.data.strip(),
            parent_phone=form.parent_phone.data.strip(),
        )
        db.session.add(student)
        db.session.commit()
        flash(f"Student '{student.name}' added successfully.", "success")
        return redirect(url_for("students.list_students"))

    return render_template("students/form.html", form=form, title="Add Student", action="add")


@students_bp.route("/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
def edit_student(student_id: int):
    """Edit an existing student record."""
    student = Student.query.get_or_404(student_id)
    form = StudentForm(obj=student)

    if form.validate_on_submit():
        # Check duplicate ID only if changed
        if form.student_id.data.strip() != student.student_id:
            existing = Student.query.filter_by(student_id=form.student_id.data.strip()).first()
            if existing:
                flash(f"Student ID '{form.student_id.data}' already exists.", "danger")
                return render_template("students/form.html", form=form, title="Edit Student", action="edit", student=student)

        student.student_id = form.student_id.data.strip()
        student.name = form.name.data.strip()
        student.department = form.department.data
        student.semester = form.semester.data
        student.parent_name = form.parent_name.data.strip()
        student.parent_phone = form.parent_phone.data.strip()
        db.session.commit()
        flash(f"Student '{student.name}' updated successfully.", "success")
        return redirect(url_for("students.list_students"))

    return render_template("students/form.html", form=form, title="Edit Student", action="edit", student=student)


@students_bp.route("/<int:student_id>/delete", methods=["POST"])
@login_required
def delete_student(student_id: int):
    """Delete a student and all related records (cascade)."""
    if not current_user.is_admin:
        abort(403)

    student = Student.query.get_or_404(student_id)
    name = student.name
    db.session.delete(student)
    db.session.commit()
    flash(f"Student '{name}' deleted.", "warning")
    return redirect(url_for("students.list_students"))


@students_bp.route("/import/template")
@login_required
def import_template():
    """Download sample CSV template for student import."""
    import io
    import csv
    from flask import Response

    output = io.StringIO()
    writer = csv.writer(output)
    # Header
    writer.writerow(["student_id", "name", "department", "semester", "parent_name", "parent_phone"])
    # Sample rows
    writer.writerow(["S101", "John Doe", "AIML", "4", "David Doe", "+919632464232"])
    writer.writerow(["S102", "Jane Smith", "AIML", "2", "Mary Smith", "+919535726772"])

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=students_import_template.csv"
    return response


@students_bp.route("/import", methods=["POST"])
@login_required
def import_students():
    """Bulk import students from CSV."""
    import io
    import csv

    file = request.files.get("file")
    if not file or not file.filename.endswith(".csv"):
        flash("Please upload a valid CSV file.", "danger")
        return redirect(url_for("students.list_students"))

    try:
        # Read the file stream
        stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
        reader = csv.DictReader(stream)
        
        # Verify headers
        fieldnames = reader.fieldnames or []
        required_headers = {"student_id", "name", "department", "semester", "parent_name", "parent_phone"}
        if not required_headers.issubset(set(fieldnames)):
            flash("Invalid CSV format. Missing required headers: " + ", ".join(required_headers), "danger")
            return redirect(url_for("students.list_students"))

        success_count = 0
        error_count = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            student_id = (row.get("student_id") or "").strip()
            name = (row.get("name") or "").strip()
            dept = (row.get("department") or "").strip()
            sem_str = (row.get("semester") or "").strip()
            p_name = (row.get("parent_name") or "").strip()
            p_phone = (row.get("parent_phone") or "").strip()

            if not (student_id and name and dept and sem_str and p_name and p_phone):
                errors.append(f"Row {row_num}: All fields are required.")
                error_count += 1
                continue

            # Duplicate ID check
            existing = Student.query.filter_by(student_id=student_id).first()
            if existing:
                errors.append(f"Row {row_num}: Student ID '{student_id}' already exists.")
                error_count += 1
                continue

            # Validate semester
            try:
                semester = int(sem_str)
                if not (1 <= semester <= 12):
                    raise ValueError
            except ValueError:
                errors.append(f"Row {row_num}: Semester must be an integer between 1 and 12.")
                error_count += 1
                continue

            # Validate department
            if dept not in DEPARTMENTS:
                errors.append(f"Row {row_num}: Department '{dept}' is invalid.")
                error_count += 1
                continue

            # Add new student
            student = Student(
                student_id=student_id,
                name=name,
                department=dept,
                semester=semester,
                parent_name=p_name,
                parent_phone=p_phone,
            )
            db.session.add(student)
            success_count += 1

        if success_count > 0:
            db.session.commit()
            flash(f"Successfully imported {success_count} students.", "success")
        
        if error_count > 0:
            error_preview = "; ".join(errors[:5])
            if len(errors) > 5:
                error_preview += f"; and {len(errors) - 5} more errors."
            flash(f"Failed to import {error_count} records. Errors: {error_preview}", "danger")

    except Exception as e:
        flash(f"Error parsing CSV file: {e}", "danger")

    return redirect(url_for("students.list_students"))
