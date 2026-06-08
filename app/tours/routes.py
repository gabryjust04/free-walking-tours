from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.auth.decorator import requires_role
from .dao import ToursDAO
from .domain import Tour


tour_bp = Blueprint("tour", __name__, url_prefix="/tours")



