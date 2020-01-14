"""
Bypass Censorship API

Allows for testing and requests for BP mirrors from an API

"""
import os
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config.from_object(os.environ['APP_SETTINGS'])

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from models import Domain, Mirror, Report, Token

@app.route('/', methods=['GET', 'POST'])
def home():
    """
    Home page of API
    """
    return "Nothing here yet!"

@app.route('/help/', methods=['GET', 'POST'])
def help():
    """
    Return help info in JSON format
    """
    return {"commands" : ['report', 'help']}

@app.route('/report/', methods=['POST'])
def report_domain():
    """
    Add report of domain to database
    """
    req_data = request.get_json()

    # is authentication token correct?

    auth_token = Token.query.filter_by(auth_token=req_data['auth_token']).first()
    if not auth_token:
        return {"report": "Unauthorized!"}

    now = datetime.datetime.now()

    # Have we seen this domain before?
    domain = Domain.query.filter_by(domain=req_data['domain']).first()

    if domain: # we've seen it before
        domain_id = domain.id
        # Have we seen the mirror before?
        mirror = Mirror.query.filter_by(mirror_url=req_data['mirror_url']).first()
        if mirror:
            mirror_id = mirror.id
        else:
            mirror = False
    else: # Let's add it
        domain = Domain(domain=req_data['domain'])
        db.session.add(domain)
        db.session.commit()
        domain_id = domain.id
        mirror = False # No domain, no mirror
 
    # Add mirror
    if not mirror:
        mirror = Mirror(
            mirror_url=req_data['mirror_url'],
            domain_id=domain_id)
        db.session.add(mirror)
        db.session.commit()
        mirror_id = mirror.id

    # Make the report
    report = Report(
        date_reported=now,
        domain_id=domain_id,
        mirror_id=mirror_id,
        location=req_data['location'],
        domain_status=req_data['domain_status'],
        mirror_status=req_data['mirror_status'],
        user_agent=req_data['user_agent'],
        ext_version=req_data['ext_version']
    )

    db.session.add(report)
    db.session.commit()

    return {"report": "Successfully reported."}

if __name__ == '__main__':
    app.run()
