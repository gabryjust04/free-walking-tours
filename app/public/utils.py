import sqlite3
import uuid
from datetime import datetime, timedelta

from flask import abort

from app.core.db import get_db
from app.core.utils import (
    CITY_NAME,
    format_duration,
    normalize_time,
    parse_time_object,
    parse_weekday_to_index,
    format_weekday,
    get_now_in_app_timezone,
    get_object_name,
    get_language_label,
    format_event_date,
    format_event_time_range,
    format_theme,
)

from app.tours.dao import (
    ToursDAO,
    TourPhotosDAO,
    TourWeeklySlotsDAO,
    TourEventsDAO,
    TourReservationsDAO,
    LanguagesDAO,
    ThemesDAO,
)


BOOKING_DAYS_AHEAD = 28
BOOKING_MAX_OCCURRENCES = 12

DEFAULT_THEME_COLOR = "#ffc107"
DEFAULT_THEME_TEXT_COLOR = "#1f1f1f"


# ---------------------------------------------------------
# Theme helpers
# ---------------------------------------------------------

def is_valid_hex_color(value):
    if value is None:
        return False

    value = str(value).strip()

    if value.startswith("#"):
        value = value[1:]

    if len(value) != 6:
        return False

    for char in value:
        if char not in "0123456789abcdefABCDEF":
            return False

    return True


def get_theme_primary_color(theme):
    color = getattr(theme, "primary_color", None)

    if not is_valid_hex_color(color):
        return DEFAULT_THEME_COLOR

    color = str(color).strip()

    if not color.startswith("#"):
        color = f"#{color}"

    return color


def get_rgb_from_hex_color(hex_color):
    color = hex_color.replace("#", "")

    red = int(color[0:2], 16)
    green = int(color[2:4], 16)
    blue = int(color[4:6], 16)

    return red, green, blue


def get_theme_rgb(theme):
    red, green, blue = get_rgb_from_hex_color(get_theme_primary_color(theme))

    return f"{red}, {green}, {blue}"


def get_theme_text_color(theme):
    red, green, blue = get_rgb_from_hex_color(get_theme_primary_color(theme))

    brightness = (red * 299 + green * 587 + blue * 114) / 1000

    if brightness > 150:
        return "#1f1f1f"

    return "#ffffff"


def get_theme_icon_filename(theme):
    icon = getattr(theme, "icon", "")

    if icon is None:
        return None

    icon = str(icon).strip()

    if icon == "":
        return None

    if "/" in icon or "\\" in icon:
        return None

    return icon


def build_theme_style(theme):
    return {
        "name": get_object_name(theme, "Walking Tour"),
        "icon_filename": get_theme_icon_filename(theme),
        "primary_color": get_theme_primary_color(theme),
        "primary_rgb": get_theme_rgb(theme),
        "text_color": get_theme_text_color(theme),
    }


# ---------------------------------------------------------
# Tour cards / common public data
# ---------------------------------------------------------

def get_cover_filename(tour_id):
    photos = TourPhotosDAO.list_photos_by_tour(tour_id)

    if photos:
        return photos[0].filename

    return None


def build_tour_card(tour):
    language = LanguagesDAO.get_language_by_id(tour.language_id)
    theme = ThemesDAO.get_theme_by_id(tour.theme_id)

    return {
        "id": tour.id,
        "title": tour.title,
        "description": tour.description,
        "meeting_point": tour.meeting_point,
        "duration": format_duration(tour.duration),
        "max_participants": tour.max_participants,
        "language": get_language_label(language),
        "theme": format_theme(theme),
        "cover_filename": get_cover_filename(tour.id),
    }


def get_public_tour_or_404(tour_id):
    tour = ToursDAO.get_tour_by_id(tour_id)

    if tour is None:
        abort(404)

    if getattr(tour, "is_deleted", 0) == 1:
        abort(404)

    return tour


# ---------------------------------------------------------
# Tour detail page
# ---------------------------------------------------------

def build_schedule_items(slots):
    schedule = []

    for slot in slots:
        schedule.append({
            "day": format_weekday(slot.day_of_week),
            "time": normalize_time(slot.start_time) or "Time not specified",
        })

    return schedule


def build_upcoming_occurrences(slots):
    now = get_now_in_app_timezone()
    today = now.date()

    occurrences = []

    for day_offset in range(BOOKING_DAYS_AHEAD + 1):
        current_date = today + timedelta(days=day_offset)

        for slot in slots:
            slot_weekday = parse_weekday_to_index(slot.day_of_week)
            slot_time = normalize_time(slot.start_time)
            slot_time_object = parse_time_object(slot.start_time)

            if slot_weekday is None or slot_time is None or slot_time_object is None:
                continue

            if current_date.weekday() != slot_weekday:
                continue

            if current_date == today and slot_time_object <= now.time():
                continue

            occurrences.append({
                "event_date": current_date.isoformat(),
                "start_time": slot_time,
                "weekday": current_date.strftime("%A"),
                "date_label": current_date.strftime("%d %b %Y"),
                "label": f"{current_date.strftime('%A, %d %b %Y')} · {slot_time}",
            })

    occurrences.sort(key=lambda item: (item["event_date"], item["start_time"]))

    return occurrences[:BOOKING_MAX_OCCURRENCES]


def build_public_tour_detail_data(tour, photos, stops, weekly_slots, theme, language):
    cover_photo = None

    if photos:
        cover_photo = photos[0]

    theme_style = build_theme_style(theme)

    return {
        "city_name": CITY_NAME,
        "tour": tour,
        "photos": photos,
        "cover_photo": cover_photo,
        "stops": stops,
        "schedule": build_schedule_items(weekly_slots),
        "upcoming_occurrences": build_upcoming_occurrences(weekly_slots),
        "theme_name": theme_style["name"],
        "theme_style": theme_style,
        "language_name": get_language_label(language),
        "duration_label": format_duration(tour.duration),
        "idempotency_key": str(uuid.uuid4()),
    }


# ---------------------------------------------------------
# Booking helpers
# ---------------------------------------------------------

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

    value = value.replace(",", "\n")

    names = []

    for line in value.splitlines():
        name = line.strip()

        if name:
            names.append(name)

    return names


def build_booking_payload(form):
    event_date, start_time = parse_occurrence_value(form.get("occurrence"))
    guest_names = parse_guest_names(form.get("additional_names", ""))

    return {
        "event_date": event_date,
        "start_time": start_time,
        "idempotency_key": form.get("idempotency_key"),
        "guest_names": guest_names,
        "additional_names": "\n".join(guest_names),
        "total_people": 1 + len(guest_names),
    }


def is_valid_occurrence(tour_id, event_date, start_time):
    start_time = normalize_time(start_time)

    if event_date is None or start_time is None:
        return False

    try:
        selected_date = datetime.strptime(event_date, "%Y-%m-%d").date()
    except ValueError:
        return False

    now = get_now_in_app_timezone()
    today = now.date()

    if selected_date < today:
        return False

    if selected_date > today + timedelta(days=BOOKING_DAYS_AHEAD):
        return False

    selected_time = parse_time_object(start_time)

    if selected_time is None:
        return False

    if selected_date == today and selected_time <= now.time():
        return False

    weekly_slots = TourWeeklySlotsDAO.list_slots_by_tour(tour_id)

    for slot in weekly_slots:
        slot_weekday = parse_weekday_to_index(slot.day_of_week)
        slot_time = normalize_time(slot.start_time)

        if selected_date.weekday() == slot_weekday and start_time == slot_time:
            return True

    return False


def get_datetime_from_event(event_date, start_time):
    start_time = normalize_time(start_time)

    if event_date is None or start_time is None:
        return None

    try:
        return datetime.strptime(f"{event_date} {start_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def find_booking_time_conflict(participant_id, event_date, start_time, duration):
    new_start = get_datetime_from_event(event_date, start_time)

    if new_start is None:
        return None

    try:
        new_end = new_start + timedelta(minutes=int(duration))
    except Exception:
        return None

    reservations = TourReservationsDAO.list_reservations_by_participant(participant_id)

    for reservation in reservations:
        if reservation.status != "active":
            continue

        event = TourEventsDAO.get_event_by_id(reservation.event_id)

        if event is None or event.event_date != event_date:
            continue

        existing_tour = ToursDAO.get_tour_by_id(event.tour_id)

        if existing_tour is None:
            continue

        existing_start = get_datetime_from_event(event.event_date, event.start_time)

        if existing_start is None:
            continue

        try:
            existing_end = existing_start + timedelta(minutes=int(existing_tour.duration))
        except Exception:
            continue

        if new_start < existing_end and existing_start < new_end:
            return existing_tour

    return None


def create_booking_for_user(tour, user, booking_payload):
    event_date = booking_payload["event_date"]
    start_time = booking_payload["start_time"]
    idempotency_key = booking_payload["idempotency_key"]
    total_people = booking_payload["total_people"]
    additional_names = booking_payload["additional_names"]

    if not idempotency_key:
        return "warning", "Invalid booking request. Please try again."

    if not is_valid_occurrence(tour.id, event_date, start_time):
        return "warning", "Please select a valid date and time."

    try:
        max_participants = int(tour.max_participants)
    except Exception:
        return "warning", "This tour is not available for booking right now."

    if max_participants <= 0:
        return "warning", "This tour is not available for booking right now."

    if total_people > max_participants:
        return "warning", f"This tour allows up to {max_participants} people per event."

    conflicting_tour = find_booking_time_conflict(
        participant_id=user.id,
        event_date=event_date,
        start_time=start_time,
        duration=tour.duration,
    )

    if conflicting_tour is not None:
        return "warning", f"You already have another booking in this time slot: {conflicting_tour.title}."

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
        print(f"Booking integrity error: {e}")

        return "warning", "This booking could not be completed. Please try again."

    except Exception as e:
        db.rollback()
        print(f"Booking error: {type(e).__name__}: {e}")

        return "danger", "Something went wrong while creating your booking."


# ---------------------------------------------------------
# My reservations page
# ---------------------------------------------------------

def build_my_reservations_page_data(participant_id):
    reservations = TourReservationsDAO.list_reservations_by_participant(participant_id)

    upcoming_reservations = []
    past_reservations = []

    now = get_now_in_app_timezone().replace(tzinfo=None)

    for reservation in reservations:
        item = build_reservation_item(reservation)

        if item is None:
            continue

        if item["event_datetime"] is not None and item["event_datetime"] >= now:
            upcoming_reservations.append(item)
        else:
            past_reservations.append(item)

    upcoming_reservations.sort(key=lambda item: item["event_datetime"] or datetime.max)
    past_reservations.sort(key=lambda item: item["event_datetime"] or datetime.min, reverse=True)

    return {
        "city_name": CITY_NAME,
        "upcoming_reservations": upcoming_reservations,
        "past_reservations": past_reservations,
    }


def build_reservation_item(reservation):
    event = TourEventsDAO.get_event_by_id(reservation.event_id)

    if event is None:
        return None

    tour = ToursDAO.get_tour_by_id(event.tour_id)

    if tour is None:
        return None

    language = LanguagesDAO.get_language_by_id(tour.language_id)
    theme = ThemesDAO.get_theme_by_id(tour.theme_id)

    event_datetime = get_datetime_from_event(event.event_date, event.start_time)
    date_parts = format_event_date(event.event_date)

    try:
        date_label = datetime.strptime(event.event_date, "%Y-%m-%d").strftime("%A, %d %b %Y")
    except Exception:
        date_label = "Date not specified"

    status = reservation.status or "active"

    status_label = status.capitalize()
    status_class = "text-bg-success"

    if status == "cancelled":
        status_label = "Cancelled"
        status_class = "text-bg-danger"
    elif event_datetime is not None and event_datetime < get_now_in_app_timezone().replace(tzinfo=None):
        status_label = "Completed"
        status_class = "text-bg-secondary"

    return {
        "id": reservation.id,
        "tour_id": tour.id,
        "title": tour.title,
        "meeting_point": tour.meeting_point,
        "theme": format_theme(theme),
        "language": get_language_label(language),
        "cover_filename": get_cover_filename(tour.id),

        "date_month": date_parts["month"],
        "date_day": date_parts["day"],
        "date_label": date_label,
        "time_range": format_event_time_range(event.start_time, tour.duration),

        "total_people": reservation.total_people,
        "guest_names": parse_guest_names(reservation.additional_names),

        "status_label": status_label,
        "status_class": status_class,
        "event_datetime": event_datetime,
    }


def build_reservation_detail_page_data(reservation_id, participant_id):
    reservation = TourReservationsDAO.get_reservation_by_id(reservation_id)

    if reservation is None:
        abort(404)

    if reservation.participant_id != participant_id:
        abort(403)

    item = build_reservation_item(reservation)

    if item is None:
        abort(404)

    event = TourEventsDAO.get_event_by_id(reservation.event_id)

    if event is None:
        abort(404)

    tour = ToursDAO.get_tour_by_id(event.tour_id)

    if tour is None:
        abort(404)

    item["can_cancel"] = can_cancel_reservation(reservation, event)
    item["cancel_limit_label"] = get_cancel_limit_label(event)

    return {
        "city_name": CITY_NAME,
        "reservation": item,
        "tour": tour,
        "raw_reservation": reservation,
    }


def can_cancel_reservation(reservation, event):
    if reservation.status != "active":
        return False

    event_datetime = get_datetime_from_event(event.event_date, event.start_time)

    if event_datetime is None:
        return False

    now = get_now_in_app_timezone().replace(tzinfo=None)

    return event_datetime - now >= timedelta(hours=24)


def get_cancel_limit_label(event):
    event_datetime = get_datetime_from_event(event.event_date, event.start_time)

    if event_datetime is None:
        return "Cancellation limit not available"

    cancel_limit = event_datetime - timedelta(hours=24)

    return cancel_limit.strftime("%A, %d %b %Y at %H:%M")


def cancel_reservation_for_user(reservation_id, participant_id):
    reservation = TourReservationsDAO.get_reservation_by_id(reservation_id)

    if reservation is None:
        return "danger", "Reservation not found."

    if reservation.participant_id != participant_id:
        return "danger", "You cannot cancel this reservation."

    event = TourEventsDAO.get_event_by_id(reservation.event_id)

    if event is None:
        return "danger", "Reservation event not found."

    if reservation.status != "active":
        return "warning", "This reservation is already cancelled."

    if not can_cancel_reservation(reservation, event):
        return "warning", "You can cancel a reservation only up to 24 hours before the tour starts."

    TourReservationsDAO.cancel_reservation(reservation.id)

    TourEventsDAO.update_actual_participants(event.id)
    get_db().commit()

    return "success", "Your reservation has been cancelled."