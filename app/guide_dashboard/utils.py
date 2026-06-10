from flask import abort
from flask_login import current_user

from app.core.utils import (
    WEEK_DAYS,
    allowed_image_file,
    process_uploaded_image,
    parse_positive_int,
    is_valid_time,
    format_duration,
    format_theme,
    get_language_label,
    format_event_date,
    format_event_time_range,
    format_stops_count,
)

from app.tours.dao import ToursDAO
from app.tours.domain import Tour


TOUR_IMAGE_SIZE = (900, 560)


def require_guide():
    if current_user.role != "guide":
        abort(403)


def get_owned_tour_or_404(tour_id):
    tour = ToursDAO.get_tour_by_id(tour_id)

    if tour is None:
        abort(404)

    if tour.guide_id != current_user.id:
        abort(403)

    return tour


def get_cover_filename(tour):
    photos = getattr(tour, "production_photos", [])

    if not photos:
        return None

    return photos[0].filename


def format_language(language):
    return get_language_label(language, "Not specified")


def build_dashboard_tours(tours):
    dashboard_tours = []

    for tour in tours:
        dashboard_tours.append({
            "id": tour.id,
            "title": tour.title,
            "description": tour.description,
            "meeting_point": tour.meeting_point,
            "duration": format_duration(tour.duration, "Duration not set"),
            "max_participants": tour.max_participants,
            "theme": format_theme(tour.theme),
            "language": format_language(tour.language),
            "cover_filename": get_cover_filename(tour),
            "stops_count": format_stops_count(tour.stops),
            "status": "ACTIVE",
        })

    return dashboard_tours


def build_dashboard_events(events):
    dashboard_events = []

    for event in events:
        if event.tour is None:
            continue

        formatted_date = format_event_date(event.event_date)

        participants = getattr(event, "actual_participants", 0)

        dashboard_events.append({
            "id": event.id,
            "title": event.tour.title,
            "theme": format_theme(event.tour.theme),
            "date_month": formatted_date["month"],
            "date_day": formatted_date["day"],
            "time_range": format_event_time_range(event.start_time, event.tour.duration),
            "participants": participants,
            "meeting_point": event.tour.meeting_point,
            "status": event.status,
        })

    return dashboard_events


def process_tour_photo(photo_file):
    return process_uploaded_image(
        photo_file=photo_file,
        upload_folder_name="tours",
        image_size=TOUR_IMAGE_SIZE,
        filename_prefix="tour",
    )


def save_uploaded_tour_photos(photo_files, tour_id, photos_dao):
    for photo_file in photo_files:
        if photo_file.filename == "":
            continue

        if not allowed_image_file(photo_file.filename):
            continue

        filename = process_tour_photo(photo_file)
        photos_dao.add_photo(tour_id, filename)


def get_tour_form_data(form):
    return {
        "title": form.get("title", "").strip(),
        "description": form.get("description", "").strip(),
        "meeting_point": form.get("meeting_point", "").strip(),
        "theme_id": form.get("theme_id", "").strip(),
        "language_id": form.get("language_id", "").strip(),
        "duration": form.get("duration", "").strip(),
        "max_participants": form.get("max_participants", "").strip(),
    }


def validate_tour_form(data):
    errors = []

    if not all([
        data["title"],
        data["description"],
        data["meeting_point"],
        data["theme_id"],
        data["language_id"],
        data["duration"],
        data["max_participants"],
    ]):
        errors.append("You must fill all required fields.")
        return errors

    if parse_positive_int(data["duration"]) is None:
        errors.append("Duration must be a positive number.")

    if parse_positive_int(data["max_participants"]) is None:
        errors.append("Max participants must be a positive number.")

    return errors


def build_tour_from_form(data, guide_id, tour_id=""):
    return Tour(
        id=tour_id,
        guide_id=guide_id,
        theme_id=int(data["theme_id"]),
        language_id=int(data["language_id"]),
        title=data["title"],
        description=data["description"],
        meeting_point=data["meeting_point"],
        duration=int(data["duration"]),
        max_participants=int(data["max_participants"]),
    )


def build_form_data_from_tour(tour):
    return {
        "title": tour.title,
        "description": tour.description,
        "meeting_point": tour.meeting_point,
        "theme_id": str(tour.theme_id),
        "language_id": str(tour.language_id),
        "duration": str(tour.duration),
        "max_participants": str(tour.max_participants),
    }


def get_schedule_form_data(form):
    selected_days = form.getlist("schedule_days")

    schedule_items = []
    errors = []
    schedule_data = {}

    for day in WEEK_DAYS:
        day_value = day["value"]

        if day_value in selected_days:
            start_time = form.get(f"start_time_{day_value}", "").strip()
            schedule_data[day_value] = start_time

            if start_time == "":
                errors.append(f"Select a start time for {day['label']}.")
            elif not is_valid_time(start_time):
                errors.append(f"Invalid start time for {day['label']}.")
            else:
                schedule_items.append({
                    "day_of_week": day_value,
                    "start_time": start_time,
                })

    return schedule_items, schedule_data, errors


def build_schedule_data_from_slots(slots):
    schedule_data = {}

    for slot in slots:
        schedule_data[slot.day_of_week] = slot.start_time

    return schedule_data


def format_schedule_label(slots):
    if not slots:
        return "No schedule yet"

    parts = []

    for slot in slots:
        day_label = slot.day_of_week[:3].capitalize()
        parts.append(f"{day_label} {slot.start_time}")

    return " · ".join(parts)


def get_stops_form_data(form):
    stop_names = form.getlist("stop_name")
    stop_descriptions = form.getlist("stop_description")

    stop_items = []
    stop_data = []
    errors = []

    max_len = max(len(stop_names), len(stop_descriptions))

    for index in range(max_len):
        stop_name = ""
        description = ""

        if index < len(stop_names):
            stop_name = stop_names[index].strip()

        if index < len(stop_descriptions):
            description = stop_descriptions[index].strip()

        if stop_name == "" and description == "":
            continue

        if stop_name == "":
            errors.append("Each stop must have a name.")
            continue

        stop_order = len(stop_items) + 1

        item = {
            "stop_name": stop_name,
            "description": description,
            "stop_order": stop_order,
        }

        stop_items.append(item)
        stop_data.append(item)

    return stop_items, stop_data, errors


def build_stop_data_from_stops(stops):
    stop_data = []

    for stop in stops:
        stop_data.append({
            "stop_name": stop.stop_name,
            "description": stop.description,
            "stop_order": stop.stop_order,
        })

    return stop_data