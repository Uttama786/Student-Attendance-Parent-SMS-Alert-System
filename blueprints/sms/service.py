"""
blueprints/sms/service.py -- Twilio SMS helper.

Public API:
  send_absence_sms(student, subject, date_str) -> SMSLog
    Sends an SMS to the student's parent and records the attempt in SMSLog.
    If Twilio credentials are not configured, logs to console instead (dev mode).
"""
import logging
from datetime import datetime

from flask import current_app

from extensions import db
from models import SMSLog, SMSDeliveryStatus

logger = logging.getLogger(__name__)

# ─────────────────────────── SMS Template ────────────────────────────────────

SMS_TEMPLATE = (
    "Dear Parent,\n"
    "Your child {student_name} was absent for {subject_name} on {date}.\n"
    "Please contact the college if required.\n"
    "-- Attendance Management System"
)


def build_message(student_name: str, subject_name: str, date: str) -> str:
    """Return the formatted SMS body."""
    return SMS_TEMPLATE.format(
        student_name=student_name,
        subject_name=subject_name,
        date=date,
    )


def send_absence_sms(student, subject: str, date_str: str):
    """
    Send an absence notification SMS to the student's parent.

    Args:
        student:   Student ORM instance
        subject:   Subject name (string)
        date_str:  Human-readable date string (e.g. Monday, 16 June 2026)

    Returns:
        SMSLog instance (committed to DB)
    """
    message_body = build_message(
        student_name=student.name,
        subject_name=subject,
        date=date_str,
    )

    # Determine Twilio configuration availability
    account_sid = current_app.config.get("TWILIO_ACCOUNT_SID", "")
    auth_token = current_app.config.get("TWILIO_AUTH_TOKEN", "")
    from_number = current_app.config.get("TWILIO_FROM_NUMBER", "")

    # Consider Twilio configured only if all three values are non-empty
    # and the SID looks real (not the placeholder ACxxx...)
    twilio_configured = bool(
        account_sid and auth_token and from_number
        and not account_sid.startswith("ACxx")
        and len(account_sid) > 10
    )

    delivery_status = SMSDeliveryStatus.PENDING
    twilio_sid = None
    error_message = None

    # Normalise recipient phone to E.164 format
    to_number = student.parent_phone.strip()
    to_number = "".join(c for c in to_number if c.isdigit() or c == "+")
    if to_number and not to_number.startswith("+"):
        if len(to_number) == 10:
            to_number = "+91" + to_number
        else:
            to_number = "+" + to_number

    if twilio_configured:
        delivery_status, twilio_sid, error_message = _send_via_twilio(
            account_sid, auth_token, from_number,
            to_number, message_body,
        )
    else:
        # Development fallback -- log to console
        logger.warning(
            "[SMS CONSOLE] To: %s\n%s", to_number, message_body
        )
        delivery_status = SMSDeliveryStatus.SENT
        twilio_sid = "CONSOLE_FALLBACK"

    # Persist to audit log
    log_entry = SMSLog(
        student_id=student.id,
        parent_phone=to_number,
        message=message_body,
        sent_time=datetime.utcnow(),
        delivery_status=delivery_status,
        twilio_sid=twilio_sid,
        error_message=error_message,
    )
    db.session.add(log_entry)
    db.session.commit()

    return log_entry


def _send_via_twilio(
    account_sid: str,
    auth_token: str,
    from_number: str,
    to_number: str,
    body: str,
) -> tuple:
    """
    Internal helper -- calls the Twilio REST API.
    Returns (SMSDeliveryStatus, message_sid, error_message).
    """
    try:
        from twilio.rest import Client

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number,
        )
        logger.info("Twilio SMS sent -- SID: %s  Status: %s", message.sid, message.status)
        return SMSDeliveryStatus.SENT, message.sid, None

    except Exception as exc:  # noqa: BLE001
        logger.error("Twilio SMS failed: %s", exc)
        import re
        # Strip ANSI colors/escape sequences
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        error_msg = ansi_escape.sub('', str(exc)).strip()
        return SMSDeliveryStatus.FAILED, None, error_msg
