from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.tours.dao import (
    ToursDAO,
    TourEventsDAO,
    TourPhotosDAO,
    ThemesDAO,
    LanguagesDAO
)

from .utils import (
    build_dashboard_tours,
    build_dashboard_events,
    get_tour_form_data,
    validate_tour_form,
    build_tour_from_form,
    build_form_data_from_tour,
    save_uploaded_tour_photos
)


guide_dashboard_bp = Blueprint("guide_dashboard", __name__)


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


@guide_dashboard_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    require_guide()

    tours = ToursDAO.list_tours_by_guide(current_user.id)

    for tour in tours:
        tour.theme = ThemesDAO.get_theme_by_id(tour.theme_id)
        tour.language = LanguagesDAO.get_language_by_id(tour.language_id)
        tour.production_photos = TourPhotosDAO.list_photos_by_tour(tour.id)

    events = TourEventsDAO.list_events_by_guide(current_user.id)

    for event in events:
        event.tour = ToursDAO.get_tour_by_id(event.tour_id)

        if event.tour is not None:
            event.tour.theme = ThemesDAO.get_theme_by_id(event.tour.theme_id)
            event.tour.language = LanguagesDAO.get_language_by_id(event.tour.language_id)

    dashboard_tours = build_dashboard_tours(tours)
    dashboard_events = build_dashboard_events(events)

    return render_template(
        "guide_dashboard/dashboard.html",
        dashboard_tours=dashboard_tours,
        dashboard_events=dashboard_events
    )


@guide_dashboard_bp.route("/dashboard/tours/new", methods=["GET", "POST"])
@login_required
def create_tour():
    require_guide()

    themes = ThemesDAO.list_all_themes()
    languages = LanguagesDAO.list_all_languages()

    if request.method == "GET":
        return render_template(
            "guide_dashboard/tour_form.html",
            mode="create",
            page_title="Create Tour",
            submit_label="Create Tour",
            themes=themes,
            languages=languages,
            form_data={},
            photos=[]
        )

    form_data = get_tour_form_data(request.form)
    errors = validate_tour_form(form_data)

    if errors:
        for error in errors:
            flash(error, "warning")

        return render_template(
            "guide_dashboard/tour_form.html",
            mode="create",
            page_title="Create Tour",
            submit_label="Create Tour",
            themes=themes,
            languages=languages,
            form_data=form_data,
            photos=[]
        )

    tour = build_tour_from_form(form_data, current_user.id)

    tour_id = ToursDAO.add_tour(tour)

    photo_files = request.files.getlist("tour_photos")
    save_uploaded_tour_photos(photo_files, tour_id, TourPhotosDAO)

    flash("Tour created successfully.", "success")
    return redirect(url_for("guide_dashboard.update_tour", tour_id=tour_id))


@guide_dashboard_bp.route("/dashboard/tours/<tour_id>/edit", methods=["GET", "POST"])
@login_required
def update_tour(tour_id):
    require_guide()

    tour = get_owned_tour_or_404(tour_id)

    themes = ThemesDAO.list_all_themes()
    languages = LanguagesDAO.list_all_languages()
    photos = TourPhotosDAO.list_photos_by_tour(tour.id)

    if request.method == "GET":
        form_data = build_form_data_from_tour(tour)

        return render_template(
            "guide_dashboard/tour_form.html",
            mode="update",
            page_title="Update Tour",
            submit_label="Save Changes",
            themes=themes,
            languages=languages,
            form_data=form_data,
            photos=photos,
            tour=tour
        )

    form_data = get_tour_form_data(request.form)
    errors = validate_tour_form(form_data)

    if errors:
        for error in errors:
            flash(error, "warning")

        return render_template(
            "guide_dashboard/tour_form.html",
            mode="update",
            page_title="Update Tour",
            submit_label="Save Changes",
            themes=themes,
            languages=languages,
            form_data=form_data,
            photos=photos,
            tour=tour
        )

    updated_tour = build_tour_from_form(form_data, current_user.id, tour.id)
    ToursDAO.update_tour(updated_tour)

    photo_files = request.files.getlist("tour_photos")
    save_uploaded_tour_photos(photo_files, tour.id, TourPhotosDAO)

    flash("Tour updated successfully.", "success")
    return redirect(url_for("guide_dashboard.update_tour", tour_id=tour.id))


@guide_dashboard_bp.route("/dashboard/tours/<tour_id>/photos/<photo_id>/delete", methods=["POST"])
@login_required
def delete_tour_photo(tour_id, photo_id):
    require_guide()

    tour = get_owned_tour_or_404(tour_id)

    photo = TourPhotosDAO.get_photo_by_id(photo_id)

    if photo is None:
        abort(404)

    if photo.tour_id != tour.id:
        abort(403)

    TourPhotosDAO.delete_photo(photo.id)

    flash("Photo removed.", "success")
    return redirect(url_for("guide_dashboard.update_tour", tour_id=tour.id))