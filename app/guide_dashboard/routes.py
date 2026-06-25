from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.tours.dao import (
    ToursDAO,
    TourEventsDAO,
    TourPhotosDAO,
    TourStopsDAO,
    TourWeeklySlotsDAO,
    ThemesDAO,
    LanguagesDAO,
)

from .utils import (
    require_guide,
    get_owned_tour_or_404,
    get_owned_event_or_404,
    tour_has_active_bookings,
    build_dashboard_tours,
    build_dashboard_event_lists,
    build_event_detail_page_data,
    save_event_evidence_photo,
    get_tour_form_data,
    validate_tour_form,
    validate_guide_schedule_overlaps,
    build_tour_from_form,
    build_form_data_from_tour,
    save_uploaded_tour_photos,
    validate_tour_photo_files,
    MIN_TOUR_PHOTOS,
    WEEK_DAYS,
    get_schedule_form_data,
    build_schedule_data_from_slots,
    get_stops_form_data,
    build_stop_data_from_stops,
)


guide_dashboard_bp = Blueprint("guide_dashboard", __name__)


@guide_dashboard_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    require_guide()

    tours = ToursDAO.list_tours_by_guide(current_user.id)

    for tour in tours:
        tour.theme = ThemesDAO.get_theme_by_id(tour.theme_id)
        tour.language = LanguagesDAO.get_language_by_id(tour.language_id)
        tour.production_photos = TourPhotosDAO.list_photos_by_tour(tour.id)
        tour.weekly_slots = TourWeeklySlotsDAO.list_slots_by_tour(tour.id)
        tour.stops = TourStopsDAO.list_stops_by_tour(tour.id)

    events = TourEventsDAO.list_events_by_guide(current_user.id)

    for event in events:
        event.tour = ToursDAO.get_tour_by_id(event.tour_id)

        if event.tour is not None:
            event.tour.theme = ThemesDAO.get_theme_by_id(event.tour.theme_id)
            event.tour.language = LanguagesDAO.get_language_by_id(event.tour.language_id)

    dashboard_event_lists = build_dashboard_event_lists(events)

    return render_template(
        "guide_dashboard/dashboard.html",
        dashboard_tours=build_dashboard_tours(tours),
        **dashboard_event_lists,
    )


@guide_dashboard_bp.route("/dashboard/events/<event_id>", methods=["GET"])
@login_required
def event_detail(event_id):
    require_guide()

    event = get_owned_event_or_404(event_id)
    page_data = build_event_detail_page_data(event)

    return render_template(
        "guide_dashboard/event_detail.html",
        **page_data,
    )


@guide_dashboard_bp.route("/dashboard/events/<event_id>/evidence-photo", methods=["POST"])
@login_required
def upload_event_evidence_photo(event_id):
    require_guide()

    event = get_owned_event_or_404(event_id)

    flash_category, flash_message = save_event_evidence_photo(
        event=event,
        photo_file=request.files.get("evidence_photo"),
        actual_participants=request.form.get("actual_participants"),
    )

    flash(flash_message, flash_category)

    return redirect(url_for("guide_dashboard.event_detail", event_id=event.id))


@guide_dashboard_bp.route("/dashboard/tours/new", methods=["GET", "POST"])
@login_required
def create_tour():
    require_guide()

    themes = ThemesDAO.list_all_themes()
    languages = LanguagesDAO.list_languages_by_guide(current_user.id)

    if request.method == "GET":
        return render_template(
            "guide_dashboard/tour_form.html",
            mode="create",
            page_title="Create Tour",
            submit_label="Create Tour",
            themes=themes,
            languages=languages,
            form_data={},
            photos=[],
            week_days=WEEK_DAYS,
            schedule_data={},
            stop_data=[],
        )

    form_data = get_tour_form_data(request.form)

    schedule_items, schedule_data, schedule_errors = get_schedule_form_data(request.form)
    stop_items, stop_data, stop_errors = get_stops_form_data(request.form)

    photo_files = request.files.getlist("tour_photos")
    selected_photo_files, photo_errors = validate_tour_photo_files(
        photo_files,
        existing_photos_count=0,
    )

    errors = validate_tour_form(form_data,current_user.id)
    errors.extend(schedule_errors)
    errors.extend(stop_errors)
    errors.extend(photo_errors)
    errors.extend(validate_guide_schedule_overlaps(
        guide_id=current_user.id,
        schedule_items=schedule_items,
        duration=form_data["duration"],
    ))

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
            photos=[],
            week_days=WEEK_DAYS,
            schedule_data=schedule_data,
            stop_data=stop_data,
        )

    tour = build_tour_from_form(form_data, current_user.id)

    tour_id = ToursDAO.add_tour(tour)

    TourWeeklySlotsDAO.replace_slots_for_tour(tour_id, schedule_items)
    TourStopsDAO.replace_stops_for_tour(tour_id, stop_items)
    save_uploaded_tour_photos(selected_photo_files, tour_id, TourPhotosDAO)

    flash("Tour created successfully.", "success")
    return redirect(url_for("guide_dashboard.update_tour", tour_id=tour_id))


@guide_dashboard_bp.route("/dashboard/tours/<tour_id>/edit", methods=["GET", "POST"])
@login_required
def update_tour(tour_id):
    require_guide()

    tour = get_owned_tour_or_404(tour_id)

    if tour_has_active_bookings(tour.id):
        flash("You cannot edit this tour because it already has active bookings.", "warning")
        return redirect(url_for("guide_dashboard.dashboard"))

    themes = ThemesDAO.list_all_themes()
    languages = LanguagesDAO.list_languages_by_guide(current_user.id)
    photos = TourPhotosDAO.list_photos_by_tour(tour.id)
    slots = TourWeeklySlotsDAO.list_slots_by_tour(tour.id)
    stops = TourStopsDAO.list_stops_by_tour(tour.id)

    if request.method == "GET":
        return render_template(
            "guide_dashboard/tour_form.html",
            mode="update",
            page_title="Update Tour",
            submit_label="Save Changes",
            themes=themes,
            languages=languages,
            form_data=build_form_data_from_tour(tour),
            photos=photos,
            tour=tour,
            week_days=WEEK_DAYS,
            schedule_data=build_schedule_data_from_slots(slots),
            stop_data=build_stop_data_from_stops(stops),
        )

    form_data = get_tour_form_data(request.form)

    schedule_items, schedule_data, schedule_errors = get_schedule_form_data(request.form)
    stop_items, stop_data, stop_errors = get_stops_form_data(request.form)

    photo_files = request.files.getlist("tour_photos")
    selected_photo_files, photo_errors = validate_tour_photo_files(
        photo_files,
        existing_photos_count=len(photos),
    )

    errors = validate_tour_form(form_data, current_user.id)
    errors.extend(schedule_errors)
    errors.extend(stop_errors)
    errors.extend(photo_errors)
    errors.extend(validate_guide_schedule_overlaps(
        guide_id=current_user.id,
        schedule_items=schedule_items,
        duration=form_data["duration"],
        current_tour_id=tour.id,
    ))

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
            tour=tour,
            week_days=WEEK_DAYS,
            schedule_data=schedule_data,
            stop_data=stop_data,
        )

    updated_tour = build_tour_from_form(form_data, current_user.id, tour.id)

    ToursDAO.update_tour(updated_tour)
    TourWeeklySlotsDAO.replace_slots_for_tour(tour.id, schedule_items)
    TourStopsDAO.replace_stops_for_tour(tour.id, stop_items)
    save_uploaded_tour_photos(selected_photo_files, tour.id, TourPhotosDAO)

    flash("Tour updated successfully.", "success")
    return redirect(url_for("guide_dashboard.update_tour", tour_id=tour.id))


@guide_dashboard_bp.route("/dashboard/tours/<tour_id>/photos/<photo_id>/delete", methods=["POST"])
@login_required
def delete_tour_photo(tour_id, photo_id):
    require_guide()

    tour = get_owned_tour_or_404(tour_id)

    if tour_has_active_bookings(tour.id):
        flash("You cannot modify photos because this tour already has active bookings.", "warning")
        return redirect(url_for("guide_dashboard.dashboard"))

    photo = TourPhotosDAO.get_photo_by_id(photo_id)

    if photo is None:
        abort(404)

    if photo.tour_id != tour.id:
        abort(403)

    photos = TourPhotosDAO.list_photos_by_tour(tour.id)

    if len(photos) <= MIN_TOUR_PHOTOS:
        flash(f"A tour must have at least {MIN_TOUR_PHOTOS} photos.", "warning")
        return redirect(url_for("guide_dashboard.update_tour", tour_id=tour.id))

    TourPhotosDAO.delete_photo(photo.id)

    flash("Photo removed.", "success")
    return redirect(url_for("guide_dashboard.update_tour", tour_id=tour.id))


@guide_dashboard_bp.route("/dashboard/tours/<tour_id>/delete", methods=["POST"])
@login_required
def delete_tour(tour_id):
    require_guide()

    tour = get_owned_tour_or_404(tour_id)

    if tour_has_active_bookings(tour.id):
        flash("You cannot delete this tour because it already has active bookings.", "warning")
        return redirect(url_for("guide_dashboard.dashboard"))

    ToursDAO.soft_delete_tour(tour.id)

    flash("Tour deleted successfully.", "success")
    return redirect(url_for("guide_dashboard.dashboard"))
