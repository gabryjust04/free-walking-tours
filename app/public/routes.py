from flask import Blueprint, render_template

from app.tours.dao import ToursDAO, TourPhotosDAO


public_bp = Blueprint("public", __name__)

CITY_NAME = "Stockholm"


def format_duration(minutes):
    if minutes is None:
        return "Durata non indicata"

    if minutes < 60:
        return f"{minutes} min"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if remaining_minutes == 0:
        return f"{hours}h"

    return f"{hours}h {remaining_minutes}min"


def format_language(language_id):
    languages = {
        "it": "IT",
        "en": "EN",
        "es": "ES",
        "fr": "FR"
    }

    if language_id is None:
        return "IT"

    language_id = str(language_id).lower()

    if language_id in languages:
        return languages[language_id]

    return language_id.upper()


@public_bp.route("/")
def home():
    tours = ToursDAO.list_all_tours(limit=6)

    tour_cards = []

    for tour in tours:
        photos = TourPhotosDAO.list_photos_by_tour(tour.id)

        cover_filename = None
        if len(photos) > 0:
            cover_filename = photos[0].filename

        tour_cards.append({
            "id": tour.id,
            "title": tour.title,
            "description": tour.description,
            "meeting_point": tour.meeting_point,
            "duration": format_duration(tour.duration),
            "max_participants": tour.max_participants,
            "language": format_language(tour.language_id),
            "cover_filename": cover_filename
        })

    return render_template(
        "home.html",
        city_name=CITY_NAME,
        tours=tour_cards
    )