import datetime
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app
from app.models import User, Token, Domain, Mirror, Report, LogReport, DomainGroup, DGDomain
from app.forms import UserForm, DomainForm, DomainGroupForm
from . import db
from . import admin_utilities
import repo_utilities

"""
Automation Routes - adding automation functions to Web interface
"""


@app.route('/alternatives/add')
@login_required
def add_alternative():
    """
    Add new alternative
    """
    pass

@app.route('/alternatives/edit/<id>')
@login_required
def edit_alternative(id):
    """
    Edit alternative
    """
    pass
