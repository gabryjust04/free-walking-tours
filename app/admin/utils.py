from flask import abort
from flask_login import current_user

from app.auth.dao import UsersDAO

from app.core.utils import (
    CITY_NAME,
    format_duration,
    format_theme,
    get_language_label,
    format_stops_count,
    format_weekday,
    normalize_time,
)

from app.tours.dao import (
    ToursDAO,
    TourPhotosDAO,
    TourStopsDAO,
    TourWeeklySlotsDAO,
    TourReservationsDAO,
    ThemesDAO,
    LanguagesDAO,
)


def require_admin():
    if current_user.role != "admin":
        abort(403)


def get_user_full_name(user):
    full_name = f"{user.first_name} {user.last_name}".strip()

    if full_name:
        return full_name

    if user.username:
        return user.username

    return user.email


def build_language_labels(languages):
    labels = []

    for language in languages:
        labels.append(get_language_label(language))

    return labels


def build_admin_dashboard_page_data():
    total_guides = UsersDAO.count_users_by_role("guide")
    total_participants = UsersDAO.count_users_by_role("participant")
    total_tours = ToursDAO.count_all_active_tours()
    total_reservations = TourReservationsDAO.count_all_reservations()

    stats = [
        {
            "label": "Guides",
            "value": total_guides,
            "icon": "bi-person-badge",
            "description": "Registered tour guides",
        },
        {
            "label": "Participants",
            "value": total_participants,
            "icon": "bi-people",
            "description": "Registered participants",
        },
        {
            "label": "Tours",
            "value": total_tours,
            "icon": "bi-map",
            "description": "Active tours on the platform",
        },
        {
            "label": "Reservations",
            "value": total_reservations,
            "icon": "bi-ticket-perforated",
            "description": "Total reservations created",
        },
    ]

    reservations_by_language = []

    rows = TourReservationsDAO.count_reservations_by_language()

    for row in rows:
        reservations_by_language.append({
            "language_id": row["language_id"],
            "language_name": row["language_name"],
            "reservations_count": row["reservations_count"],
        })

    return {
        "city_name": CITY_NAME,
        "stats": stats,
        "reservations_by_language": reservations_by_language,
    }


def build_admin_guide_row(guide):
    languages = LanguagesDAO.list_languages_by_guide(guide.id)

    return {
        "id": guide.id,
        "first_name": guide.first_name,
        "last_name": guide.last_name,
        "username": guide.username,
        "email": guide.email,
        "profile_photo": guide.profile_photo,
        "languages": build_language_labels(languages),
        "tours_count": ToursDAO.count_tours_by_guide(guide.id),
    }


def build_admin_guides_page_data():
    guide_users = UsersDAO.list_users_by_role("guide")

    guides = []

    for guide in guide_users:
        guides.append(build_admin_guide_row(guide))

    return {
        "city_name": CITY_NAME,
        "guides": guides,
        "guides_count": len(guides),
    }


def get_guide_or_404(guide_id):
    guide = UsersDAO.get_user_by_id(guide_id)

    if guide is None:
        abort(404)

    if guide.role != "guide":
        abort(404)

    return guide


def build_schedule_label(slots):
    if not slots:
        return "No schedule"

    parts = []

    for slot in slots:
        day_label = format_weekday(slot.day_of_week)
        start_time = normalize_time(slot.start_time) or "Time not specified"

        parts.append(f"{day_label} at {start_time}")

    return " · ".join(parts)


def build_stop_items(stops):
    stop_items = []

    for stop in stops:
        stop_items.append({
            "name": stop.stop_name,
            "description": stop.description,
            "order": stop.stop_order,
        })

    return stop_items


def build_admin_tour_item(tour):
    theme = ThemesDAO.get_theme_by_id(tour.theme_id)
    language = LanguagesDAO.get_language_by_id(tour.language_id)

    photos = TourPhotosDAO.list_photos_by_tour(tour.id)
    stops = TourStopsDAO.list_stops_by_tour(tour.id)
    slots = TourWeeklySlotsDAO.list_slots_by_tour(tour.id)

    return {
        "id": tour.id,
        "title": tour.title,
        "description": tour.description,
        "meeting_point": tour.meeting_point,
        "duration": format_duration(tour.duration),
        "max_participants": tour.max_participants,

        "theme": format_theme(theme),
        "language": get_language_label(language),

        "photos_count": len(photos),
        "stops_count": format_stops_count(stops),
        "stops": build_stop_items(stops),
        "schedule": build_schedule_label(slots),

        "reservations_count": TourReservationsDAO.count_reservations_by_tour(tour.id),
    }


def build_admin_guide_profile(guide):
    languages = LanguagesDAO.list_languages_by_guide(guide.id)

    return {
        "id": guide.id,
        "first_name": guide.first_name,
        "last_name": guide.last_name,
        "username": guide.username,
        "email": guide.email,
        "profile_photo": guide.profile_photo,
        "full_name": get_user_full_name(guide),
        "languages": build_language_labels(languages),
    }


def build_admin_guide_detail_page_data(guide_id):
    guide = get_guide_or_404(guide_id)
    tours = ToursDAO.list_tours_by_guide(guide.id)

    tour_items = []

    for tour in tours:
        tour_items.append(build_admin_tour_item(tour))

    return {
        "city_name": CITY_NAME,
        "guide": build_admin_guide_profile(guide),
        "tours": tour_items,
        "tours_count": len(tour_items),
    }