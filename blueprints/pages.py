from flask import Blueprint, render_template

from blueprints.auth import login_required

pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/")
@login_required
def dashboard():
    return render_template("dashboard.html")


@pages_bp.get("/offerings")
@login_required
def offerings_page():
    return render_template("offerings.html")


@pages_bp.get("/upload_offering")
@login_required
def upload_offering_page():
    return render_template("upload_offering.html")


@pages_bp.get("/opportunity")
@login_required
def opportunity_page():
    return render_template("opportunity.html")


@pages_bp.get("/create_opportunity")
@login_required
def create_opportunity_page():
    return render_template("create_opportunity.html")


@pages_bp.get("/upload_case")
@login_required
def upload_case_page():
    return render_template("upload_case.html")