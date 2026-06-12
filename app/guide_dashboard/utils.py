from datetime import datetime, timedelta

from flask import abort
from flask_login import current_user

from app.auth.dao import UsersDAO
from app.core.utils import (
    WEEK_DAYS,
    process_uploaded_image,
    validate_uploaded_image,
    parse_positive_int,
    is_valid_time,
    normalize_time,
    parse_weekday_to_index,
    format_weekday,
    get_now_in_app_timezone,
    format_duration,
    format_theme,
    get_language_label,
    format_event_date,
    format_event_time_range,
    format_stops_count,
)

from app.tours.dao import (
    ToursDAO,
    TourEventsDAO,
    TourReservationsDAO,
    TourWeeklySlotsDAO,
)

from app.tours.domain import Tour


TOUR_IMAGE_SIZE = (900, 560)
EVIDENCE_IMAGE_SIZE = (900, 560)

MIN_TOUR_PHOTOS = 5
MIN_TOUR_IMAGE_WIDTH = 400
MIN_TOUR_IMAGE_HEIGHT = 200

MIN_EVIDENCE_IMAGE_WIDTH = 400
MIN_EVIDENCE_IMAGE_HEIGHT = 200


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


def get_owned_event_or_404(event_id):
    event = TourEventsDAO.get_event_by_id(event_id)

    if event is None:
        abort(404)

    tour = ToursDAO.get_tour_by_id(event.tour_id)

    if tour is None:
        abort(404)

    if tour.guide_id != current_user.id:
        abort(403)

    event.tour = tour

    return event


def tour_has_active_bookings(tour_id):
    events = TourEventsDAO.list_events_by_tour(tour_id)

    for event in events:
        if event.status != "scheduled":
            continue
        reservations = TourReservationsDAO.list_reservations_by_event(event.id)

        for reservation in reservations:
            if reservation.status == "active" and int(reservation.total_people or 0) > 0:
                return True

    return False


def get_cover_filename(tour):
    photos = getattr(tour, "production_photos", [])

    if photos:
        return photos[0].filename

    return None


def get_event_start_datetime(event):
    start_time = normalize_time(event.start_time)

    if start_time is None:
        return None

    try:
        return datetime.strptime(
            f"{event.event_date} {start_time}",
            "%Y-%m-%d %H:%M"
        )
    except Exception:
        return None


def has_event_started(event):
    event_start = get_event_start_datetime(event)

    if event_start is None:
        return False

    now = get_now_in_app_timezone().replace(tzinfo=None)

    return event_start <= now


def get_event_status_label(event):
    if event.status == "completed":
        return "Completed"

    if event.status == "cancelled":
        return "Cancelled"

    if has_event_started(event):
        return "Ongoing"

    return "Scheduled"


def get_event_status_class(event):
    status_label = get_event_status_label(event)

    if status_label == "Completed":
        return "text-bg-secondary"

    if status_label == "Ongoing":
        return "text-bg-warning"

    if status_label == "Cancelled":
        return "text-bg-danger"

    return "text-bg-success"


def can_upload_evidence_photo(event):
    if event.status == "completed":
        return False

    if event.status == "cancelled":
        return False

    return has_event_started(event)


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
            "language": get_language_label(tour.language),
            "cover_filename": get_cover_filename(tour),
            "stops_count": format_stops_count(tour.stops),
            "status": "ACTIVE",
        })

    return dashboard_tours


def build_dashboard_event_item(event):
    if event.tour is None:
        return None

    formatted_date = format_event_date(event.event_date)

    return {
        "id": event.id,
        "title": event.tour.title,
        "theme": format_theme(event.tour.theme),
        "date_month": formatted_date["month"],
        "date_day": formatted_date["day"],
        "time_range": format_event_time_range(event.start_time, event.tour.duration),
        "participants": getattr(event, "actual_participants", 0),
        "meeting_point": event.tour.meeting_point,
        "status_label": get_event_status_label(event),
        "status_class": get_event_status_class(event),
        "sort_date": get_event_start_datetime(event),
    }


def build_dashboard_event_lists(events):
    upcoming_events = []
    ongoing_events = []
    past_events = []

    for event in events:
        item = build_dashboard_event_item(event)

        if item is None:
            continue

        if event.status == "completed":
            past_events.append(item)
        elif has_event_started(event):
            ongoing_events.append(item)
        else:
            upcoming_events.append(item)

    upcoming_events.sort(key=lambda item: item["sort_date"] or datetime.max)
    ongoing_events.sort(key=lambda item: item["sort_date"] or datetime.max)
    past_events.sort(key=lambda item: item["sort_date"] or datetime.min, reverse=True)

    return {
        "dashboard_upcoming_events": upcoming_events,
        "dashboard_ongoing_events": ongoing_events,
        "dashboard_past_events": past_events,
    }


def build_event_detail_page_data(event):
    tour = event.tour

    formatted_date = format_event_date(event.event_date)
    reservations = TourReservationsDAO.list_reservations_by_event(event.id)

    active_people = 0
    participants = []

    for reservation in reservations:
        user = UsersDAO.get_user_by_id(reservation.participant_id)

        if reservation.status == "active":
            active_people += int(reservation.total_people or 0)

        participants.append(build_participant_row(reservation, user))

    max_participants = parse_positive_int(tour.max_participants) or 0
    available_places = max(max_participants - active_people, 0)

    return {
        "event": {
            "id": event.id,
            "tour_id": tour.id,
            "title": tour.title,
            "theme": format_theme(tour.theme),
            "language": get_language_label(tour.language),
            "date_month": formatted_date["month"],
            "date_day": formatted_date["day"],
            "date_label": format_full_date(event.event_date),
            "time_range": format_event_time_range(event.start_time, tour.duration),
            "meeting_point": tour.meeting_point,
            "status_label": get_event_status_label(event),
            "status_class": get_event_status_class(event),
            "active_people": active_people,
            "max_participants": max_participants,
            "available_places": available_places,
            "can_upload_evidence": can_upload_evidence_photo(event),
            "evidence_photo": getattr(event, "evidence_photo", None),
        },
        "participants": participants,
    }


def build_participant_row(reservation, user):
    status_class = "text-bg-success"

    if reservation.status == "cancelled":
        status_class = "text-bg-danger"
    elif reservation.status != "active":
        status_class = "text-bg-secondary"

    return {
        "id": reservation.id,
        "participant_name": get_user_display_name(user),
        "participant_email": getattr(user, "email", "Email not available"),
        "total_people": reservation.total_people,
        "guest_names": split_guest_names(reservation.additional_names),
        "status": reservation.status.capitalize(),
        "status_class": status_class,
        "created_at": format_created_at(reservation.created_at),
    }


def get_user_display_name(user):
    if user is None:
        return "Unknown participant"

    full_name = f"{user.first_name} {user.last_name}".strip()

    if full_name:
        return full_name

    if user.username:
        return user.username

    return user.email


def split_guest_names(value):
    if not value:
        return []

    names = []

    for line in value.splitlines():
        name = line.strip()

        if name:
            names.append(name)

    return names


def format_full_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%A, %d %b %Y")
    except Exception:
        return "Date not specified"


def format_created_at(value):
    if not value:
        return "-"

    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y, %H:%M")
    except Exception:
        return value


def get_selected_photo_files(photo_files):
    selected_files = []

    for photo_file in photo_files:
        if photo_file is not None and photo_file.filename != "":
            selected_files.append(photo_file)

    return selected_files


def validate_tour_photo_files(photo_files, existing_photos_count=0):
    selected_files = get_selected_photo_files(photo_files)
    errors = []

    total_photos = existing_photos_count + len(selected_files)

    if total_photos < MIN_TOUR_PHOTOS:
        errors.append(f"Upload at least {MIN_TOUR_PHOTOS} tour photos.")

    for photo_file in selected_files:
        is_valid, error = validate_uploaded_image(
            photo_file,
            min_width=MIN_TOUR_IMAGE_WIDTH,
            min_height=MIN_TOUR_IMAGE_HEIGHT,
        )

        if not is_valid:
            errors.append(f"{photo_file.filename}: {error}")

    return selected_files, errors


def process_tour_photo(photo_file):
    return process_uploaded_image(
        photo_file=photo_file,
        upload_folder_name="tours",
        image_size=TOUR_IMAGE_SIZE,
        filename_prefix="tour",
        min_width=MIN_TOUR_IMAGE_WIDTH,
        min_height=MIN_TOUR_IMAGE_HEIGHT,
    )


def save_uploaded_tour_photos(photo_files, tour_id, photos_dao):
    for photo_file in photo_files:
        filename = process_tour_photo(photo_file)
        photos_dao.add_photo(tour_id, filename)


def process_evidence_photo(photo_file):
    return process_uploaded_image(
        photo_file=photo_file,
        upload_folder_name="evidence_photos",
        image_size=EVIDENCE_IMAGE_SIZE,
        filename_prefix="evidence",
        min_width=MIN_EVIDENCE_IMAGE_WIDTH,
        min_height=MIN_EVIDENCE_IMAGE_HEIGHT,
    )


def save_event_evidence_photo(event, photo_file):
    if photo_file is None or photo_file.filename == "":
        return "warning", "Upload an evidence photo."

    if not can_upload_evidence_photo(event):
        return "warning", "You can upload evidence only after the event has started."

    is_valid, error = validate_uploaded_image(
        photo_file,
        min_width=MIN_EVIDENCE_IMAGE_WIDTH,
        min_height=MIN_EVIDENCE_IMAGE_HEIGHT,
    )

    if not is_valid:
        return "warning", error

    try:
        filename = process_evidence_photo(photo_file)
    except Exception:
        return "danger", "Error processing evidence photo."

    TourEventsDAO.complete_event_with_evidence_photo(event.id, filename)

    return "success", "Evidence photo uploaded. Event marked as completed."


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

    required_fields = [
        data["title"],
        data["description"],
        data["meeting_point"],
        data["theme_id"],
        data["language_id"],
        data["duration"],
        data["max_participants"],
    ]

    if not all(required_fields):
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
    schedule_data = {}
    errors = []

    for day in WEEK_DAYS:
        day_value = day["value"]

        if day_value not in selected_days:
            continue

        start_time = form.get(f"start_time_{day_value}", "").strip()
        schedule_data[day_value] = start_time

        if start_time == "":
            errors.append(f"Select a start time for {day['label']}.")
            continue

        if not is_valid_time(start_time):
            errors.append(f"Invalid start time for {day['label']}.")
            continue

        schedule_items.append({
            "day_of_week": day_value,
            "start_time": normalize_time(start_time),
        })

    return schedule_items, schedule_data, errors


def build_schedule_data_from_slots(slots):
    schedule_data = {}

    for slot in slots:
        schedule_data[slot.day_of_week] = normalize_time(slot.start_time)

    return schedule_data


def get_minutes_from_time(value):
    value = normalize_time(value)

    if value is None:
        return None

    try:
        hours, minutes = value.split(":")
        return int(hours) * 60 + int(minutes)
    except Exception:
        return None


def times_overlap(first_start, first_duration, second_start, second_duration):
    first_start_minutes = get_minutes_from_time(first_start)
    second_start_minutes = get_minutes_from_time(second_start)

    first_duration = parse_positive_int(first_duration)
    second_duration = parse_positive_int(second_duration)

    if (
        first_start_minutes is None
        or second_start_minutes is None
        or first_duration is None
        or second_duration is None
    ):
        return False

    first_end_minutes = first_start_minutes + first_duration
    second_end_minutes = second_start_minutes + second_duration

    return first_start_minutes < second_end_minutes and second_start_minutes < first_end_minutes


def validate_guide_schedule_overlaps(guide_id, schedule_items, duration, current_tour_id=None):
    errors = []
    duration = parse_positive_int(duration)

    if duration is None:
        return errors

    guide_tours = ToursDAO.list_tours_by_guide(guide_id)

    for existing_tour in guide_tours:
        if current_tour_id is not None and existing_tour.id == current_tour_id:
            continue

        existing_slots = TourWeeklySlotsDAO.list_slots_by_tour(existing_tour.id)

        for new_slot in schedule_items:
            for existing_slot in existing_slots:
                new_day = parse_weekday_to_index(new_slot["day_of_week"])
                existing_day = parse_weekday_to_index(existing_slot.day_of_week)

                if new_day is None or existing_day is None:
                    continue

                if new_day != existing_day:
                    continue

                if not times_overlap(
                    new_slot["start_time"],
                    duration,
                    existing_slot.start_time,
                    existing_tour.duration,
                ):
                    continue

                day_label = format_weekday(new_slot["day_of_week"])
                existing_time_range = format_event_time_range(
                    existing_slot.start_time,
                    existing_tour.duration,
                )
                new_time_range = format_event_time_range(
                    new_slot["start_time"],
                    duration,
                )

                errors.append(
                    f"Schedule conflict on {day_label}: "
                    f"{new_time_range} overlaps with '{existing_tour.title}' ({existing_time_range})."
                )

    return errors


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

        item = {
            "stop_name": stop_name,
            "description": description,
            "stop_order": len(stop_items) + 1,
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