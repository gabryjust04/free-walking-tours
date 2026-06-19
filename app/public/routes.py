from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.core.utils import CITY_NAME
from app.tours.dao import (
    ToursDAO,
    TourPhotosDAO,
    TourStopsDAO,
    TourWeeklySlotsDAO,
    ThemesDAO,
    LanguagesDAO,
)

from .utils import (
    build_my_reservations_page_data,
    build_reservation_detail_page_data,
    build_tour_card,
    build_tour_listings_page_data,
    cancel_reservation_for_user,
    get_public_tour_or_404,
    build_public_tour_detail_data,
    build_booking_payload,
    create_booking_for_user,
)


public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def home():
    tours = ToursDAO.list_all_tours(limit=6)
    languages = LanguagesDAO.list_all_languages()

    tour_cards = []

    for tour in tours:
        tour_cards.append(build_tour_card(tour))

    return render_template(
        "home.html",
        city_name=CITY_NAME,
        tours=tour_cards,
        languages=languages,
    )


@public_bp.route("/tours")
def tour_listings():
    page_data = build_tour_listings_page_data(request.args)

    return render_template(
        "listings.html",
        **page_data,
    )


@public_bp.route("/tours/<tour_id>")
def tour_detail(tour_id):
    tour = get_public_tour_or_404(tour_id)

    photos = TourPhotosDAO.list_photos_by_tour(tour.id)
    stops = TourStopsDAO.list_stops_by_tour(tour.id)
    weekly_slots = TourWeeklySlotsDAO.list_slots_by_tour(tour.id)

    theme = ThemesDAO.get_theme_by_id(tour.theme_id)
    language = LanguagesDAO.get_language_by_id(tour.language_id)

    template_data = build_public_tour_detail_data(
        tour=tour,
        photos=photos,
        stops=stops,
        weekly_slots=weekly_slots,
        theme=theme,
        language=language,
    )

    return render_template("tour_detail.html", **template_data)


@public_bp.route("/tours/<tour_id>/book", methods=["POST"])
@login_required
def book_tour(tour_id):
    tour = get_public_tour_or_404(tour_id)

    if getattr(current_user, "role", None) == "guide":
        flash("Guides cannot book tours.", "warning")
        return redirect(url_for("public.tour_detail", tour_id=tour.id))

    booking_payload = build_booking_payload(request.form)

    flash_category, flash_message = create_booking_for_user(
        tour=tour,
        user=current_user,
        booking_payload=booking_payload,
    )

    flash(flash_message, flash_category)

    return redirect(url_for("public.tour_detail", tour_id=tour.id))


@public_bp.route("/my-reservations")
@login_required
def my_reservations():
    page_data = build_my_reservations_page_data(current_user.id)

    return render_template(
        "my_reservations.html",
        **page_data,
    )


@public_bp.route("/my-reservations/<reservation_id>")
@login_required
def reservation_detail(reservation_id):
    page_data = build_reservation_detail_page_data(
        reservation_id=reservation_id,
        participant_id=current_user.id,
    )

    return render_template(
        "reservation_detail.html",
        **page_data,
    )


@public_bp.route("/my-reservations/<reservation_id>/cancel", methods=["POST"])
@login_required
def cancel_reservation(reservation_id):
    flash_category, flash_message = cancel_reservation_for_user(
        reservation_id=reservation_id,
        participant_id=current_user.id,
    )

    flash(flash_message, flash_category)

    return redirect(url_for("public.reservation_detail", reservation_id=reservation_id))