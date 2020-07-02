import datetime
from flask import request
from app import app
from app.models import Token, Domain, Mirror, Report
from . import db
from repo_utilities import check

## API

## V2 Routes

@app.route('/api/v2/help', methods=['GET','POST'])
def help_v2():
    """
    Return help info in JSON format
    """
    return {"commands" : ['report', 'help', 'alternatives']}

def domains_v2():
    """
    Returns in JSON format all alternatives for a domain/url
    """
    # Auth token in headers
    try:
        auth_token = Token.query.filter_by(auth_token=request.headers['Authorization']).first()
    except:
        return {"report" : "Database Error with token!"}
    if not auth_token:
        return {"report": "Unauthorized!"}

    return check(request.args['domain'], '2')


## V1 Routes --- To Be Deprecated ---

@app.route('/api/v1/help/', methods=['GET', 'POST'])
def help():
    """
    Return help info in JSON format
    """
    return {"commands" : ['report', 'help', 'domains']}

@app.route('/api/v1/domain/', methods=['GET', 'POST'])
def domains():
    """
    Returns in JSON format all alternatives for a domain/url
    """
    # is authentication token correct?
    try:
        auth_token = Token.query.filter_by(auth_token=request.args['auth_token']).first()
    except:
        return {"report" : "Database Error with token!"}
    if not auth_token:
        return {"report": "Unauthorized!"}

    exists, available_mirrors, available_onions, available_ipfs_nodes = check(request.args['domain'], '1')

    return {
        'domain':request.args['domain'],
        'available_mirrors': available_mirrors,
        'available_onions': available_onions,
        'available_ipfs_nodes': available_ipfs_nodes
        }

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
