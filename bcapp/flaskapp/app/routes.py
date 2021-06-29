import datetime
from flask import render_template, redirect, url_for, request, flash, abort, jsonify
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from app import app
from app.models import User, Domain
from . import db
import repo_utilities
import mirror_tests
from .admin_utilities import get_domain_group
from system_utilities import send_email, get_configs

@app.route('/')
def home():
    """
    Home page of APP
    """
    domain_list = Domain.query.filter((Domain.inactive==None) | (Domain.inactive!=True)).all()
    domains = []
    for dom in domain_list:
        domains.append(dom.domain)
    return render_template('index.html',
                            title='Home',
                            domains=domains)

@app.route('/public_alternatives', methods=['GET'])
def public_alternatives():
    """
    Listing Alternatives
    """
    if request.args.get('url'):
        alternatives = request.args.get('alternatives')
        url = request.args.get('url')
        if '.onion' in url:
            status, final_url = mirror_tests.test_onion(url, 'web')
            if status != 200:
                result = 'down'
            else:
                result = 'up'
        else:
            status, final_url = mirror_tests.test_domain(url, '', 'web', '')
            if status != 200:
                result = 'down'
            else:
                result = 'up'
    else:
        url = False
        result = 'none'
    
    domain_choice = request.args.get('domain_choice')
    alternatives_list = repo_utilities.check(domain_choice)
    if not alternatives_list['exists']:
        alternatives = False
    else:
        alternatives = alternatives_list['available_alternatives']
    return render_template('public_alternatives.html',
                            title='Home',
                            domain_choice=domain_choice,
                            alternatives=alternatives,
                            url=url,
                            result=result)


@app.route('/profile')
@login_required
def profile():
    """
    Profile
    """
    # TODO: add list of available reports for the domain this user is a part of
    domain_group = get_domain_group(current_user.id)
    return render_template('profile.html', user=current_user, domain_group=domain_group)

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

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    configs = get_configs()
    if request.method == 'POST': # Got an email address
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            # create token
            token = secrets.token_hex(20)
            message = f"You recently requested a password reset. Please visit this url to reset your password: {configs['web_url']}/forgot_password?token={token}"
            sent = send_email(email, "Password Reset", message)
            if sent:
                user.last_token = token
                db.session.commit()
                flash('Sent reset information by email')
            return redirect(url_for('home'))
        else:
            flash('No user by that email address!')
            return redirect(url_for('home'))
    elif request.method == 'GET':
        if request.args.get('token'): #Got a token
            user = User.query.filter_by(last_token=request.args.get('token')).all()
            if user:
                return render_template('new_password.html', user=user)
            else:
                flash('Unauthorized!')
                return redirect(url_for('home'))
        else:
            return render_template('reset_password.html')   
            

@app.route('/set_password', methods=['POST'])
def set_password():
    user_id = request.form.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    if user:
        user.password = generate_password_hash(request.form.get('password'))
        db.session.commit()
        flash('Password Reset. Login Now')
        return redirect(url_for('login'))
    else:
        flash('Invalid user!')
        return redirect(url_for('home'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Error handling

@app.errorhandler(404)
def resource_not_found(e):
    return jsonify(error=str(e)), 404

