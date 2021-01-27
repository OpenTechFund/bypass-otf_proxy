import datetime
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app
from app.models import User, Domain
from . import db
import mirror_tests

@app.route('/', methods=['GET'])
def home():
    """
    Home page of APP
    """
    domain_list = Domain.query.all()
    domains = []
    if request.args.get('domain_choice'):
        domain_choice = request.args.get('domain_choice')
        mirror_details = mirror_tests.mirror_detail(domain=domain_choice, mode='web', proxy='')
        print(mirror_details)
        alt_domain = mirror_details['domain']
        current_alternatives = mirror_details['current_alternatives']
    else:
        alt_domain = False
        current_alternatives = False
    
    for dom in domain_list:
        domains.append(dom.domain)
    return render_template('index.html',
                            title='Home',
                            domains=domains,
                            alt_domain=alt_domain,
                            current_alternatives=current_alternatives)

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
