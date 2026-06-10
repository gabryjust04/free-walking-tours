import re
import os
import uuid

from PIL import Image, ImageOps

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from .dao import UsersDAO
from .domain import User
from app.core.login_manager import login_manager
from app.tours.dao import LanguagesDAO
from .utils import (
    get_signup_form_data,
    get_profile_form_data,
    validate_signup_form_data,
    validate_profile_form_data,
    get_profile_photo_filename,
    build_user_for_signup,
    build_user_for_profile_update,
)

auth_bp = Blueprint("auth", __name__)

PROFILE_IMG_SIZE = 130
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def is_valid_email(email):
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(email_regex, email) is not None


def is_valid_password(password):
    return (
        len(password) >= 8
        and any(c.isupper() for c in password)
        and any(c.isdigit() for c in password)
    )


def allowed_file(filename):
    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def process_profile_photo(photo_file):
    ext = photo_file.filename.rsplit(".", 1)[1].lower()
    safe_filename = f"img_{uuid.uuid4()}.{ext}"

    img = Image.open(photo_file)

    img = ImageOps.fit(
        img,
        (PROFILE_IMG_SIZE, PROFILE_IMG_SIZE),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5)
    )

    upload_folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "pics"
    )

    os.makedirs(upload_folder, exist_ok=True)

    img.save(os.path.join(upload_folder, safe_filename))

    return safe_filename


def get_selected_language_ids(form):
    selected_language_ids = form.getlist("language_ids")
    cleaned_language_ids = []

    for language_id in selected_language_ids:
        try:
            cleaned_language_ids.append(int(language_id))
        except Exception:
            continue

    return cleaned_language_ids


def are_valid_language_ids(language_ids, available_languages):
    available_ids = [language.id for language in available_languages]

    for language_id in language_ids:
        if language_id not in available_ids:
            return False

    return True


@login_manager.user_loader
def load_user(user_id):
    return UsersDAO.get_user_by_id(user_id)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    languages = LanguagesDAO.list_all_languages()

    if request.method == "GET":
        return render_template(
            "signup.html",
            languages=languages,
        )

    form_data = get_signup_form_data(request.form)

    errors = validate_signup_form_data(form_data, languages)

    for error in errors:
        flash(error, "warning")

    if errors:
        return redirect(url_for("auth.signup"))

    if UsersDAO.get_user_by_email(form_data["email"]):
        flash("Email already used", "warning")
        return redirect(url_for("auth.signup"))

    if UsersDAO.get_user_by_username(form_data["username"]):
        flash("Username already used", "warning")
        return redirect(url_for("auth.signup"))

    try:
        img_filename = get_profile_photo_filename(
            request.files.get("profile_photo"),
            "default.png",
        )
    except Exception:
        flash("Error processing image.", "danger")
        return redirect(url_for("auth.signup"))

    user = build_user_for_signup(form_data, img_filename)

    if UsersDAO.add_user(user):
        flash("Registration was successful, now you can login", "success")
        return redirect(url_for("auth.login"))

    flash("System error, try again", "danger")
    return redirect(url_for("auth.signup"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    user = UsersDAO.get_user_by_email(email)

    if user is None:
        flash("Invalid email or password", "danger")
        return redirect(url_for("auth.login"))

    if not check_password_hash(user.password_hash, password):
        flash("Invalid email or password", "danger")
        return redirect(url_for("auth.login"))

    login_user(user, remember=True)

    flash(f"Welcome back {user.first_name}!", "success")
    return redirect(url_for("public.home"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("public.home"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    languages = LanguagesDAO.list_all_languages()

    if request.method == "GET":
        selected_language_ids = []

        if current_user.role == "guide":
            selected_language_ids = current_user.guide_language_ids

        return render_template(
            "profile.html",
            user=current_user,
            languages=languages,
            selected_language_ids=selected_language_ids,
        )

    form_data = get_profile_form_data(request.form, current_user)

    errors = validate_profile_form_data(form_data, current_user, languages)

    for error in errors:
        flash(error, "warning")

    if errors:
        return redirect(url_for("auth.profile"))

    user_with_same_email = UsersDAO.get_user_by_email(form_data["email"])

    if user_with_same_email is not None and user_with_same_email.id != current_user.id:
        flash("Email already used by another account", "warning")
        return redirect(url_for("auth.profile"))

    user_with_same_username = UsersDAO.get_user_by_username(form_data["username"])

    if user_with_same_username is not None and user_with_same_username.id != current_user.id:
        flash("Username already taken", "warning")
        return redirect(url_for("auth.profile"))

    password_hash = current_user.password_hash

    if form_data["new_password"]:
        password_hash = generate_password_hash(form_data["new_password"])

    try:
        img_filename = get_profile_photo_filename(
            request.files.get("profile_photo"),
            current_user.profile_photo,
        )
    except Exception:
        flash("Error processing new image.", "danger")
        return redirect(url_for("auth.profile"))

    updated_user = build_user_for_profile_update(
        data=form_data,
        current_user=current_user,
        password_hash=password_hash,
        profile_photo_filename=img_filename,
    )

    if not UsersDAO.update_user(updated_user):
        flash("Error updating profile.", "danger")
        return redirect(url_for("auth.profile"))

    if current_user.role == "guide":
        if not UsersDAO.replace_guide_languages(current_user.id, form_data["guide_language_ids"]):
            flash("Profile updated, but guide languages could not be saved.", "warning")
            return redirect(url_for("auth.profile"))

    flash("Profile updated successfully.", "success")
    return redirect(url_for("auth.profile"))