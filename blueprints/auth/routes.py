"""
blueprints/auth/routes.py — Authentication blueprint.

Routes:
  GET  /login  — Show login form
  POST /login  — Validate credentials and create session
  GET  /logout — Clear session and redirect to login
"""
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, session,
)
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length

from models import Faculty

auth_bp = Blueprint("auth", __name__, template_folder="../../templates/auth")


# ─────────────────────────────── Forms ───────────────────────────────────────

class LoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(message="Username is required"), Length(max=80)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Password is required")],
    )
    remember = BooleanField("Remember Me")


# ─────────────────────────────── Routes ──────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Render the login page and process credentials."""
    # Already authenticated — redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()

    if form.validate_on_submit():
        user = Faculty.query.filter_by(username=form.username.data.strip()).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f"Welcome back, {user.name}!", "success")

            # Honour the 'next' parameter for deferred redirects
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))

        flash("Invalid username or password. Please try again.", "danger")

    return render_template("auth/login.html", form=form, title="Sign In")


@auth_bp.route("/logout")
@login_required
def logout():
    """Clear the user session and redirect to login."""
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))
