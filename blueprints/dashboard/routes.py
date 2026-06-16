"""
blueprints/dashboard/routes.py — Dashboard statistics and chart data.

Routes:
  GET /           — Main dashboard with KPI cards and attendance doughnut chart
  GET /api/stats  — JSON endpoint consumed by Chart.js (today's attendance breakdown)
"""
from datetime import date

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from extensions import db
from models import Student, Attendance, SMSLog, AttendanceStatus

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../../templates/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    """Render the main dashboard page with aggregated statistics."""
    today = date.today()

    total_students = Student.query.count()

    # Today's attendance counts
    present_today = (
        Attendance.query
        .filter(Attendance.date == today, Attendance.status == AttendanceStatus.PRESENT)
        .count()
    )
    absent_today = (
        Attendance.query
        .filter(Attendance.date == today, Attendance.status == AttendanceStatus.ABSENT)
        .count()
    )
    sms_today = (
        SMSLog.query
        .filter(func.date(SMSLog.sent_time) == today)
        .count()
    )

    # Recent SMS logs (last 10)
    recent_sms = (
        SMSLog.query
        .order_by(SMSLog.sent_time.desc())
        .limit(10)
        .all()
    )

    # Department-wise student distribution
    dept_data = (
        db.session.query(Student.department, func.count(Student.id))
        .group_by(Student.department)
        .all()
    )

    # Last 7 days attendance trend
    from datetime import timedelta
    trend_labels = []
    trend_present = []
    trend_absent = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        trend_labels.append(d.strftime("%d %b"))
        p = Attendance.query.filter(
            Attendance.date == d, Attendance.status == AttendanceStatus.PRESENT
        ).count()
        a = Attendance.query.filter(
            Attendance.date == d, Attendance.status == AttendanceStatus.ABSENT
        ).count()
        trend_present.append(p)
        trend_absent.append(a)

    return render_template(
        "dashboard/index.html",
        title="Dashboard",
        total_students=total_students,
        present_today=present_today,
        absent_today=absent_today,
        sms_today=sms_today,
        recent_sms=recent_sms,
        dept_labels=[d[0] for d in dept_data],
        dept_counts=[d[1] for d in dept_data],
        trend_labels=trend_labels,
        trend_present=trend_present,
        trend_absent=trend_absent,
    )


@dashboard_bp.route("/api/stats")
@login_required
def api_stats():
    """JSON endpoint for live chart refresh."""
    today = date.today()
    total = Student.query.count()
    present = Attendance.query.filter(
        Attendance.date == today, Attendance.status == AttendanceStatus.PRESENT
    ).count()
    absent = Attendance.query.filter(
        Attendance.date == today, Attendance.status == AttendanceStatus.ABSENT
    ).count()
    return jsonify({"total": total, "present": present, "absent": absent})
