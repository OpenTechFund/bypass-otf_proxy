import datetime
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app
from app.models import User, Token, Domain, Mirror, Report
from . import db

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
    return render_template('profile.html', name=current_user.name)

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/admin')
@login_required
def admin():
    """
    Administration
    """
    if current_user.admin:
        return render_template('admin.html', name=current_user.name)
    else:
        flash('Have to be an admin!')
        return redirect(url_for('profile'))

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
    return render_template('login.html')\

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

## API (to be a separate blueprint?)
@app.route('/api/v1/help/', methods=['GET', 'POST'])
def help():
    """
    Return help info in JSON format
    """
    return {"commands" : ['report', 'help']}

@app.route('/api/v1/report/', methods=['POST'])
def report_domain():
    """
    Add report of domain to database
    """
    req_data = request.get_json()

    # is authentication token correct?

    try:
        auth_token = Token.query.filter_by(auth_token=req_data['auth_token']).first()
    except:
        return {"report" : "Database Error with token!"}
    if not auth_token:
        return {"report": "Unauthorized!"}

    now = datetime.datetime.now()

    # Have we seen this domain before?
    try:
        domain = Domain.query.filter_by(domain=req_data['domain']).first()
    except:
        return {"report" : "Database Error with domain query!"}

    if domain: # we've seen it before
        domain_id = domain.id
        # Have we seen the mirror before?
        try:
            mirror = Mirror.query.filter_by(mirror_url=req_data['mirror_url']).first()
        except:
            return {"report" : "Database Error with mirror query!"}
        if mirror:
            mirror_id = mirror.id
        else:
            mirror = False
    else: # Let's add it
        try:
            domain = Domain(domain=req_data['domain'])
            db.session.add(domain)
            db.session.commit()
        except:
            return {"report" : "Database Error with mirror addition!"}
        domain_id = domain.id
        mirror = False # No domain, no mirror
 
    # Add mirror
    if not mirror:
        mirror = Mirror(
            mirror_url=req_data['mirror_url'],
            domain_id=domain_id)
        try:
            db.session.add(mirror)
            db.session.commit()
        except:
            return {"report" : "Database Error with mirror addition!"}
        mirror_id = mirror.id

    # Make the report
    req_data['date_reported'] = now
    req_data['domain_id'] = domain_id
    req_data['mirror_id'] = mirror_id
    req_data.pop('domain')
    req_data.pop('mirror_url')
    try:
        report = Report(**req_data)
        db.session.add(report)
        db.session.commit()
    except:
        return {"report" : "Database Error with report!"}


    return {"report": "Successfully reported."}
