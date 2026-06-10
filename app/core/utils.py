import os
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from PIL import Image, ImageOps
from flask import current_app
from werkzeug.utils import secure_filename


CITY_NAME = "Stockholm"
APP_TIMEZONE = "Europe/Stockholm"

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

WEEK_DAYS = [
    {"value": "monday", "label": "Monday", "short": "Mon"},
    {"value": "tuesday", "label": "Tuesday", "short": "Tue"},
    {"value": "wednesday", "label": "Wednesday", "short": "Wed"},
    {"value": "thursday", "label": "Thursday", "short": "Thu"},
    {"value": "friday", "label": "Friday", "short": "Fri"},
    {"value": "saturday", "label": "Saturday", "short": "Sat"},
    {"value": "sunday", "label": "Sunday", "short": "Sun"},
]


def get_object_value(obj, attr_name, default=None):
    if obj is None:
        return default

    value = getattr(obj, attr_name, default)

    if value is None:
        return default

    return value


def get_object_name(obj, fallback="Not specified"):
    return get_object_value(obj, "name", fallback)


def parse_positive_int(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None

    if number <= 0:
        return None

    return number


def format_duration(minutes, fallback="Duration not specified"):
    minutes = parse_positive_int(minutes)

    if minutes is None:
        return fallback

    if minutes < 60:
        return f"{minutes} min"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if remaining_minutes == 0:
        return f"{hours}h"

    return f"{hours}h {remaining_minutes}min"


def normalize_time(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    accepted_formats = ["%H:%M", "%H:%M:%S"]

    for accepted_format in accepted_formats:
        try:
            parsed_time = datetime.strptime(value, accepted_format).time()
            return parsed_time.strftime("%H:%M")
        except ValueError:
            pass

    if len(value) >= 5:
        return value[:5]

    return None


def parse_time_object(value):
    normalized = normalize_time(value)

    if normalized is None:
        return None

    try:
        return datetime.strptime(normalized, "%H:%M").time()
    except ValueError:
        return None


def is_valid_time(value):
    return parse_time_object(value) is not None


def parse_weekday_to_index(day):
    if day is None:
        return None

    value = str(day).strip().lower()

    weekdays = {
        "monday": 0,
        "mon": 0,
        "0": 0,
        "1": 0,

        "tuesday": 1,
        "tue": 1,
        "2": 1,

        "wednesday": 2,
        "wed": 2,
        "3": 2,

        "thursday": 3,
        "thu": 3,
        "4": 3,

        "friday": 4,
        "fri": 4,
        "5": 4,

        "saturday": 5,
        "sat": 5,
        "6": 5,

        "sunday": 6,
        "sun": 6,
        "7": 6,
    }

    return weekdays.get(value)


def format_weekday(day):
    weekday_index = parse_weekday_to_index(day)

    labels = {
        0: "Monday",
        1: "Tuesday",
        2: "Wednesday",
        3: "Thursday",
        4: "Friday",
        5: "Saturday",
        6: "Sunday",
    }

    if weekday_index in labels:
        return labels[weekday_index]

    return "Day not specified"


def get_now_in_app_timezone():
    return datetime.now(ZoneInfo(APP_TIMEZONE))


def format_event_date(event_date):
    try:
        date_obj = datetime.strptime(event_date, "%Y-%m-%d")
    except Exception:
        return {
            "month": "---",
            "day": "--",
        }

    return {
        "month": date_obj.strftime("%b").upper(),
        "day": date_obj.strftime("%d"),
    }


def format_event_time_range(start_time, duration):
    normalized_start_time = normalize_time(start_time)

    if normalized_start_time is None:
        return "Time not specified"

    try:
        duration = int(duration)
        start = datetime.strptime(normalized_start_time, "%H:%M")
        end = start + timedelta(minutes=duration)

        return f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}"
    except Exception:
        return normalized_start_time


def get_language_label(language, fallback="Not specified"):
    if language is None:
        return fallback

    label = getattr(language, "label", None)
    code = getattr(language, "code", None)
    slug = getattr(language, "slug", None)
    name = getattr(language, "name", None)
    language_id = getattr(language, "id", None)

    if label:
        return str(label).upper()

    if code:
        return str(code).upper()

    if slug:
        return str(slug).upper()

    if name:
        return str(name)

    if language_id:
        return str(language_id).upper()

    return fallback


def format_theme(theme, fallback="Walking Tour"):
    return get_object_name(theme, fallback)


def format_stops_count(stops):
    if not stops:
        return "No stops yet"

    if len(stops) == 1:
        return "1 stop"

    return f"{len(stops)} stops"


def allowed_image_file(filename, allowed_extensions=None):
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_IMAGE_EXTENSIONS

    if filename is None:
        return False

    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()

    return extension in allowed_extensions


def process_uploaded_image(photo_file, upload_folder_name, image_size, filename_prefix):
    original_filename = secure_filename(photo_file.filename)

    if not allowed_image_file(original_filename):
        raise ValueError("Invalid image format.")

    extension = original_filename.rsplit(".", 1)[1].lower()
    new_filename = f"{filename_prefix}_{uuid.uuid4()}.{extension}"

    img = Image.open(photo_file)
    img = ImageOps.exif_transpose(img)

    img = ImageOps.fit(
        img,
        image_size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )

    if extension in {"jpg", "jpeg"} and img.mode in {"RGBA", "P"}:
        img = img.convert("RGB")

    upload_folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        upload_folder_name,
    )

    os.makedirs(upload_folder, exist_ok=True)

    img.save(os.path.join(upload_folder, new_filename))

    return new_filename