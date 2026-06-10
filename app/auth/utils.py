import re
import uuid

from werkzeug.security import generate_password_hash

from app.auth.domain import User
from app.core.utils import allowed_image_file, process_uploaded_image


PROFILE_IMG_SIZE = (130, 130)


def is_valid_email(email):
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(email_regex, email) is not None


def is_valid_password(password):
    return (
        len(password) >= 8
        and any(c.isupper() for c in password)
        and any(c.isdigit() for c in password)
    )


def process_profile_photo(photo_file):
    return process_uploaded_image(
        photo_file=photo_file,
        upload_folder_name="pics",
        image_size=PROFILE_IMG_SIZE,
        filename_prefix="img",
    )


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


def get_signup_form_data(form):
    return {
        "email": form.get("email", "").strip(),
        "password": form.get("password", ""),
        "first_name": form.get("first_name", "").strip(),
        "last_name": form.get("last_name", "").strip(),
        "username": form.get("username", "").strip(),
        "role": form.get("role", "participant").strip(),
        "guide_language_ids": get_selected_language_ids(form),
    }


def get_profile_form_data(form, current_user):
    guide_language_ids = []

    if current_user.role == "guide":
        guide_language_ids = get_selected_language_ids(form)

    return {
        "email": form.get("email", "").strip(),
        "first_name": form.get("first_name", "").strip(),
        "last_name": form.get("last_name", "").strip(),
        "username": form.get("username", "").strip(),
        "new_password": form.get("password", ""),
        "guide_language_ids": guide_language_ids,
    }


def validate_signup_form_data(data, languages):
    errors = []

    if not all([
        data["email"],
        data["password"],
        data["first_name"],
        data["last_name"],
        data["username"],
    ]):
        errors.append("You must fill all required fields.")

    if data["email"] and not is_valid_email(data["email"]):
        errors.append("Invalid email format.")

    if data["password"] and not is_valid_password(data["password"]):
        errors.append("Password must be at least 8 characters long, contain 1 uppercase letter and 1 number.")

    allowed_roles = ["participant", "guide"]

    if data["role"] not in allowed_roles:
        errors.append("Invalid role.")

    if data["role"] == "guide":
        if len(data["guide_language_ids"]) == 0:
            errors.append("Select at least one language if you want to register as a guide.")

        if not are_valid_language_ids(data["guide_language_ids"], languages):
            errors.append("Invalid guide language selected.")

    return errors


def validate_profile_form_data(data, current_user, languages):
    errors = []

    if not all([
        data["email"],
        data["first_name"],
        data["last_name"],
        data["username"],
    ]):
        errors.append("Email, First Name, Last Name and Username are required.")

    if data["email"] and not is_valid_email(data["email"]):
        errors.append("Invalid email format.")

    if data["new_password"] and not is_valid_password(data["new_password"]):
        errors.append("New password must be at least 8 chars, 1 uppercase, 1 number.")

    if current_user.role == "guide":
        if len(data["guide_language_ids"]) == 0:
            errors.append("Select at least one guide language.")

        if not are_valid_language_ids(data["guide_language_ids"], languages):
            errors.append("Invalid guide language selected.")

    return errors


def get_profile_photo_filename(photo_file, default_filename):
    if photo_file is None or photo_file.filename == "":
        return default_filename

    if not allowed_image_file(photo_file.filename):
        raise ValueError("Invalid image format.")

    return process_profile_photo(photo_file)


def build_user_for_signup(data, profile_photo_filename):
    guide_language_ids = data["guide_language_ids"]

    if data["role"] != "guide":
        guide_language_ids = []

    return User(
        id=str(uuid.uuid4()),
        email=data["email"],
        password_hash=generate_password_hash(data["password"]),
        first_name=data["first_name"],
        last_name=data["last_name"],
        username=data["username"],
        role=data["role"],
        profile_photo=profile_photo_filename,
        guide_language_ids=guide_language_ids,
    )


def build_user_for_profile_update(data, current_user, password_hash, profile_photo_filename):
    guide_language_ids = data["guide_language_ids"]

    if current_user.role != "guide":
        guide_language_ids = []

    return User(
        id=current_user.id,
        email=data["email"],
        password_hash=password_hash,
        first_name=data["first_name"],
        last_name=data["last_name"],
        username=data["username"],
        role=current_user.role,
        profile_photo=profile_photo_filename,
        guide_language_ids=guide_language_ids,
    )