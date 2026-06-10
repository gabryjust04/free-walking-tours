import sqlite3
import uuid
from datetime import datetime, timedelta

from flask import abort

from app.core.db import get_db
from app.core.utils import (
    CITY_NAME,
    APP_TIMEZONE,
    format_duration,
    normalize_time,
    parse_time_object,
    parse_weekday_to_index,
    format_weekday,
    get_now_in_app_timezone,
    get_object_name,
    get_language_label,
)

from app.tours.dao import (
    ToursDAO,
    TourPhotosDAO,
    TourWeeklySlotsDAO,
    TourEventsDAO,
    TourReservationsDAO,
    LanguagesDAO,
)


BOOKING_DAYS_AHEAD = 28
BOOKING_MAX_OCCURRENCES = 12


def build_tour_card(tour):
    language = LanguagesDAO.get_language_by_id(tour.language_id)

    return {
        "id": tour.id,
        "title": tour.title,
        "description": tour.description,
        "meeting_point": tour.meeting_point,
        "duration": format_duration(tour.duration),
        "max_participants": tour.max_participants,
        "language": get_language_label(language),
        "cover_filename": get_cover_filename(tour.id),
    }


def get_cover_filename(tour_id):
    photos = TourPhotosDAO.list_photos_by_tour(tour_id)

    if photos:
        return photos[0].filename

    return None


def build_schedule_items(slots):
    schedule = []

    for slot in slots:
        schedule.append({
            "day": format_weekday(slot.day_of_week),
            "time": normalize_time(slot.start_time) or "Time not specified",
        })

    return schedule


def build_upcoming_occurrences(slots, days_ahead=BOOKING_DAYS_AHEAD, max_items=BOOKING_MAX_OCCURRENCES):
    now = get_now_in_app_timezone()
    today = now.date()

    occurrences = []

    for day_offset in range(days_ahead + 1):
        current_date = today + timedelta(days=day_offset)

        for slot in slots:
            slot_weekday = parse_weekday_to_index(slot.day_of_week)
            slot_start_time = normalize_time(slot.start_time)
            slot_start_time_object = parse_time_object(slot.start_time)

            if slot_weekday is None or slot_start_time is None or slot_start_time_object is None:
                continue

            if current_date.weekday() != slot_weekday:
                continue

            if current_date == today and slot_start_time_object <= now.time():
                continue

            occurrences.append({
                "event_date": current_date.isoformat(),
                "start_time": slot_start_time,
                "weekday": current_date.strftime("%A"),
                "date_label": current_date.strftime("%d %b %Y"),
                "label": f"{current_date.strftime('%A, %d %b %Y')} · {slot_start_time}",
            })

    occurrences.sort(key=lambda item: (item["event_date"], item["start_time"]))

    return occurrences[:max_items]


def is_valid_occurrence(slots, event_date, start_time):
    normalized_start_time = normalize_time(start_time)

    if normalized_start_time is None:
        return False

    try:
        selected_date = datetime.strptime(event_date, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return False

    now = get_now_in_app_timezone()
    today = now.date()

    if selected_date < today:
        return False

    max_date = today + timedelta(days=BOOKING_DAYS_AHEAD)

    if selected_date > max_date:
        return False

    selected_time_object = parse_time_object(normalized_start_time)

    if selected_time_object is None:
        return False

    if selected_date == today and selected_time_object <= now.time():
        return False

    selected_weekday = selected_date.weekday()

    for slot in slots:
        slot_weekday = parse_weekday_to_index(slot.day_of_week)
        slot_start_time = normalize_time(slot.start_time)

        if slot_weekday == selected_weekday and slot_start_time == normalized_start_time:
            return True

    return False


def parse_occurrence_value(value):
    if value is None:
        return None, None

    value = str(value).strip()

    if "|" not in value:
        return None, None

    event_date, start_time = value.split("|", 1)

    return event_date.strip(), normalize_time(start_time)


def parse_guest_names(value):
    if value is None:
        return []

    cleaned_value = value.replace(",", "\n")

    names = []

    for line in cleaned_value.splitlines():
        name = line.strip()

        if name:
            names.append(name)

    return names


def get_public_tour_or_404(tour_id):
    tour = ToursDAO.get_tour_by_id(tour_id)

    if tour is None:
        abort(404)

    if getattr(tour, "is_deleted", 0) == 1:
        abort(404)

    return tour


def build_public_tour_detail_data(tour, photos, stops, weekly_slots, theme, language):
    cover_photo = None

    if photos:
        cover_photo = photos[0]

    return {
        "city_name": CITY_NAME,
        "tour": tour,
        "photos": photos,
        "cover_photo": cover_photo,
        "stops": stops,
        "schedule": build_schedule_items(weekly_slots),
        "upcoming_occurrences": build_upcoming_occurrences(weekly_slots),
        "theme_name": get_object_name(theme),
        "language_name": get_language_label(language),
        "duration_label": format_duration(tour.duration),
        "idempotency_key": str(uuid.uuid4()),
    }


def build_booking_payload(form):
    occurrence_value = form.get("occurrence")
    event_date, start_time = parse_occurrence_value(occurrence_value)

    additional_names_raw = form.get("additional_names", "")

    guest_names = parse_guest_names(additional_names_raw)

    return {
        "event_date": event_date,
        "start_time": start_time,
        "idempotency_key": form.get("idempotency_key"),
        "guest_names": guest_names,
        "additional_names": "\n".join(guest_names),
        "total_people": 1 + len(guest_names),
    }


def create_booking_for_user(tour, user, booking_payload):
    event_date = booking_payload["event_date"]
    start_time = booking_payload["start_time"]
    idempotency_key = booking_payload["idempotency_key"]
    total_people = booking_payload["total_people"]
    additional_names = booking_payload["additional_names"]

    if not idempotency_key:
        return "warning", "Invalid booking request. Please try again."

    weekly_slots = TourWeeklySlotsDAO.list_slots_by_tour(tour.id)

    if not is_valid_occurrence(weekly_slots, event_date, start_time):
        return "warning", "Please select a valid date and time."

    try:
        max_participants = int(tour.max_participants)
    except (TypeError, ValueError):
        return "warning", "This tour is not available for booking right now."

    if max_participants <= 0:
        return "warning", "This tour is not available for booking right now."

    if total_people > max_participants:
        return "warning", f"This tour allows up to {max_participants} people per event."

    db = get_db()

    try:
        db.execute("BEGIN IMMEDIATE")

        existing_reservation = TourReservationsDAO.get_reservation_by_idempotency_key(idempotency_key)

        if existing_reservation is not None:
            db.rollback()
            return "success", "Your booking has already been confirmed."

        event = TourEventsDAO.get_event_by_occurrence(
            tour_id=tour.id,
            event_date=event_date,
            start_time=start_time,
        )

        if event is None:
            event_id = TourEventsDAO.create_event_for_booking(
                tour_id=tour.id,
                event_date=event_date,
                start_time=start_time,
            )
        else:
            event_id = event.id

        user_already_booked = TourReservationsDAO.has_active_reservation_by_event_and_participant(
            event_id=event_id,
            participant_id=user.id,
        )

        if user_already_booked:
            db.rollback()
            return "warning", "You already have an active booking for this tour time."

        reserved_people = TourReservationsDAO.count_reserved_people(event_id)
        available_places = max_participants - reserved_people

        if total_people > available_places:
            db.rollback()

            if available_places <= 0:
                return "warning", "This tour time is fully booked."

            return "warning", f"Only {available_places} places are still available for this time."

        TourReservationsDAO.add_reservation(
            event_id=event_id,
            participant_id=user.id,
            total_people=total_people,
            additional_names=additional_names,
            idempotency_key=idempotency_key,
        )

        TourEventsDAO.update_actual_participants(event_id)

        db.commit()

        return "success", "Your booking has been confirmed."

    except sqlite3.IntegrityError as e:
        db.rollback()

        error_message = str(e)
        print(f"Booking integrity error: {error_message}")

        existing_reservation = TourReservationsDAO.get_reservation_by_idempotency_key(idempotency_key)

        if existing_reservation is not None:
            return "success", "Your booking has already been confirmed."

        if "idx_tour_reservations_one_active_per_user" in error_message:
            return "warning", "You already have an active booking for this tour time."

        if "tour_reservations.event_id" in error_message and "tour_reservations.participant_id" in error_message:
            return "warning", "You already have an active booking for this tour time."

        return "warning", "This booking could not be completed. Please try again."

    except Exception as e:
        db.rollback()
        print(f"Booking error: {type(e).__name__}: {e}")
        return "danger", "Something went wrong while creating your booking."