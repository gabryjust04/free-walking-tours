# Admin routes for dashboards, guide lists, and guide details.

from flask import Blueprint, render_template
from flask_login import login_required

from .utils import (
    require_admin,
    build_admin_dashboard_page_data,
    build_admin_guides_page_data,
    build_admin_guide_detail_page_data,
)


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# Show the admin dashboard summary.
@admin_bp.route("/")
@login_required
def dashboard():
    # Require admin role.
    require_admin()

    # Build page data.
    page_data = build_admin_dashboard_page_data()

    return render_template(
        "admin/dashboard.html",
        **page_data,
    )


# Show all guides for admin review.
@admin_bp.route("/guides")
@login_required
def guides():
    # Require admin role.
    require_admin()

    # Build page data.
    page_data = build_admin_guides_page_data()

    return render_template(
        "admin/guides.html",
        **page_data,
    )


# Show detail data for one guide.
@admin_bp.route("/guides/<guide_id>")
@login_required
def guide_detail(guide_id):
    # Require admin role.
    require_admin()

    # Build page data.
    page_data = build_admin_guide_detail_page_data(guide_id)

    return render_template(
        "admin/guide_detail.html",
        **page_data,
    )
