import datetime
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app
from app.models import User, Token, Domain, Mirror, Report, LogReport
from . import db
from . import admin_utilities

@app.route('/')
def home():
    """
    Home page of APP
    """
    return render_template('index.html', title='Home')

@app.route('/profile')
@login_required
def profile():
    """
    Profile
    """
    # TODO: add list of available reports for the domain this user is a part of
    return render_template('profile.html', name=current_user.name)

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    password = request.form.get('password')
    name = request.form.get('name')

    user = User.query.filter_by(email=email).first() # if this returns a user, then the email already exists in database

    if user: # if a user is found, we want to redirect back to signup page so user can try again
        flash('Email address already exists')
        return redirect(url_for('signup'))

    # create new user with the form data. Hash the password so plaintext version isn't saved.
    new_user = User(email=email, name=name, password=generate_password_hash(password, method='sha256'))

    # add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(email=email).first()

    # check if user actually exists
    # take the user supplied password, hash it, and compare it to the hashed password in database
    if not user or not check_password_hash(user.password, password):
        flash('Please check your login details and try again.')
        return redirect(url_for('login')) # if user doesn't exist or password is wrong, reload the page

    # if the above check passes, then we know the user has the right credentials
    login_user(user, remember=remember)
    return redirect(url_for('profile'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

### Admin

@app.route('/admin')
@login_required
def admin():
    """
    Administration
    """
    domain_list = Domain.query.all()
    domains = []
    for dom in domain_list:
        domains.append(dom.domain)
    if current_user.admin:
        report_types = [
            #{
             #   'name': 'Log Reports List',
             #   'report': 'log_reports_list'
             #},
             {
                'name': 'Recent Domain Reports',
                'report': 'recent_domain_reports'
             },
             {
                 'name': "Last Week's Bad Domains",
                 'report': 'bad_domains'
             },
             {
                 'name': "Last Week's Bad Mirrors",
                 'report': 'bad_mirrors'
             },
             {
                 'name': "Monthly Aggregate Report",
                 'report': 'monthly_bad'
             }
        ]
        return render_template('admin.html', name=current_user.name, report_types=report_types, domains=domains)
    else:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))

@app.route('/admin/log_reports')
@login_required
def log_reports_list():
    if current_user.admin:
        log_reports = admin_utilities.log_report_list()
        return render_template('log_reports_list.html', name=current_user.name, log_reports=log_reports)
    else:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))

@app.route('/admin/domain_reports', methods=['GET'])
@login_required
def recent_domain_reports():
    domain_choice = request.args.get('domain_choice')
    if current_user.admin:
        print(f"Domain choice: {domain_choice}")
        recent_reports = admin_utilities.get_recent_domain_reports(domain_choice)
        return render_template('recent_domain_reports.html', name=current_user.name, recent_reports=recent_reports, domain_choice=domain_choice)
    else:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))

@app.route('/admin/bad_domains')
@login_required
def bad_domains():
    if current_user.admin:
        bad_domains = admin_utilities.bad_domains()
        if not bad_domains:
            all_good = True
        else:
            all_good = False
        return render_template('bad_domains.html', name=current_user.name, bad_domains=bad_domains, all_good=all_good)
    else:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))

@app.route('/admin/bad_mirrors')
@login_required
def bad_mirrors():
    if current_user.admin:
        bad_mirrors = admin_utilities.bad_mirrors()
        return render_template('bad_mirrors.html', name=current_user.name, bad_mirrors=bad_mirrors)
    else:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))

@app.route('/admin/monthy_bad')
@login_required
def monthly_bad():
    if current_user.admin:
        monthly_bad = admin_utilities.monthly_bad()
        return render_template('monthly_bad.html', name=current_user.name, monthly_bad=monthly_bad)
    else:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))

## Log Reports
@app.route('/log_reports/display', methods=['GET'])
@login_required
def display_log_report():
    """
    List one report
    """
    # grab report
    log_report_id = request.args.get('id')
    log_report = LogReport.query.filter_by(id=log_report_id).first()
    domain_name = Domain.query.filter_by(id=log_report.domain_id).first().domain
    if not log_report:
        flash('No such report!')
        return redirect(url_for('admin'))
    if current_user.admin or int(current_user.domain_id) == int(log_report.domain_id):
        report_text = log_report.report.split('\n')
        return render_template('log_report.html', log_report=log_report, domain=domain_name, report_text=report_text)
    else:
        flash("Don't have access to that domain!!")
        return redirect(url_for('profile'))
