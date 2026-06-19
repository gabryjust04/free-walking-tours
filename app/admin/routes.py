from flask import Blueprint, render_template
from flask_login import login_required

from .utils import (
    require_admin,
    build_admin_dashboard_page_data,
    build_admin_guides_page_data,
    build_admin_guide_detail_page_data,
)


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
def dashboard():
    require_admin()

    page_data = build_admin_dashboard_page_data()

    return render_template(
        "admin/dashboard.html",
        **page_data,
    )


@admin_bp.route("/guides")
@login_required
def guides():
    require_admin()

    page_data = build_admin_guides_page_data()

    return render_template(
        "admin/guides.html",
        **page_data,
    )


@admin_bp.route("/guides/<guide_id>")
@login_required
def guide_detail(guide_id):
    require_admin()

    page_data = build_admin_guide_detail_page_data(guide_id)

    return render_template(
        "admin/guide_detail.html",
        **page_data,
    )