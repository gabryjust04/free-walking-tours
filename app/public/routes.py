# Public routes for browsing tours, booking tours, and managing reservations.

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


# Show the homepage with featured tours and language filters.
@public_bp.route("/")
def home():
    # Load featured tours.
    tours = ToursDAO.list_all_tours(limit=6)
    languages = LanguagesDAO.list_all_languages()

    tour_cards = []

    for tour in tours:
        # Build tour card.
        tour_cards.append(build_tour_card(tour))

    return render_template(
        "home.html",
        city_name=CITY_NAME,
        tours=tour_cards,
        languages=languages,
    )


# Show searchable public tour listings.
@public_bp.route("/tours")
def tour_listings():
    # Build listing data.
    page_data = build_tour_listings_page_data(request.args)

    return render_template(
        "listings.html",
        **page_data,
    )


# Show one public tour with photos, stops, schedule, theme, and language.
@public_bp.route("/tours/<tour_id>")
def tour_detail(tour_id):
    # Fetch public tour.
    tour = get_public_tour_or_404(tour_id)

    # Load tour details.
    photos = TourPhotosDAO.list_photos_by_tour(tour.id)
    stops = TourStopsDAO.list_stops_by_tour(tour.id)
    weekly_slots = TourWeeklySlotsDAO.list_slots_by_tour(tour.id)

    # Load metadata.
    theme = ThemesDAO.get_theme_by_id(tour.theme_id)
    language = LanguagesDAO.get_language_by_id(tour.language_id)

    # Build detail data.
    template_data = build_public_tour_detail_data(
        tour=tour,
        photos=photos,
        stops=stops,
        weekly_slots=weekly_slots,
        theme=theme,
        language=language,
    )

    return render_template("tour_detail.html", **template_data)


# Create a reservation for the signed-in participant.
@public_bp.route("/tours/<tour_id>/book", methods=["POST"])
@login_required
def book_tour(tour_id):
    # Fetch public tour.
    tour = get_public_tour_or_404(tour_id)

    role = getattr(current_user, "role", "")
    role_lower = str(role).lower()

    if role_lower in ("guide", "admin"):
        flash(f"{str(role).capitalize()}s cannot book tours.", "warning")
        return redirect(url_for("public.tour_detail", tour_id=tour.id))

    # Build booking data.
    booking_payload = build_booking_payload(request.form)

    # Create user booking.
    flash_category, flash_message = create_booking_for_user(
        tour=tour,
        user=current_user,
        booking_payload=booking_payload,
    )

    flash(flash_message, flash_category)

    return redirect(url_for("public.tour_detail", tour_id=tour.id))


# Show the signed-in user's reservations.
@public_bp.route("/my-reservations")
@login_required
def my_reservations():
    # Build page data.
    page_data = build_my_reservations_page_data(current_user.id)

    return render_template(
        "my_reservations.html",
        **page_data,
    )


# Show one reservation owned by the signed-in user.
@public_bp.route("/my-reservations/<reservation_id>")
@login_required
def reservation_detail(reservation_id):
    # Build detail data.
    page_data = build_reservation_detail_page_data(
        reservation_id=reservation_id,
        participant_id=current_user.id,
    )

    return render_template(
        "reservation_detail.html",
        **page_data,
    )


# Cancel one reservation owned by the signed-in user.
@public_bp.route("/my-reservations/<reservation_id>/cancel", methods=["POST"])
@login_required
def cancel_reservation(reservation_id):
    # Cancel reservation.
    flash_category, flash_message = cancel_reservation_for_user(
        reservation_id=reservation_id,
        participant_id=current_user.id,
    )

    flash(flash_message, flash_category)

    return redirect(url_for("public.reservation_detail", reservation_id=reservation_id))
