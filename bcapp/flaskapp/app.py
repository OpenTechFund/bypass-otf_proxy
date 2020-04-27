"""
Bypass Censorship API

Allows for testing and requests for BP mirrors from an API

"""
import os
from flask import Flask, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import datetime
import sys
sys.path.insert(0,'.')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config.from_object(os.environ['APP_SETTINGS'])

db = SQLAlchemy(app)
migrate = Migrate(app, db)

import models
#from models import Domain, Mirror, Report, Token

## APP

@app.route('/')
def home():
    """
    Home page of APP
    """
    return render_template('index.html')

@app.route('/profile')
def profile():
    """
    Profile
    """
    return render_template('profile.html')

@app.route('/login')
def login():
    """
    Login
    """
    return render_template('login.html')


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
        return {"report" : "Database Error!"}
    if not auth_token:
        return {"report": "Unauthorized!"}

    now = datetime.datetime.now()

    # Have we seen this domain before?
    try:
        domain = Domain.query.filter_by(domain=req_data['domain']).first()
    except:
        return {"report" : "Database Error!"}

    if domain: # we've seen it before
        domain_id = domain.id
        # Have we seen the mirror before?
        try:
            mirror = Mirror.query.filter_by(mirror_url=req_data['mirror_url']).first()
        except:
            return {"report" : "Database Error!"}
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
            return {"report" : "Database Error!"}
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
            return {"report" : "Database Error!"}
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
        return {"report" : "Database Error!"}


    return {"report": "Successfully reported."}
