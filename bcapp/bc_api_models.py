"""
Models for BC API
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/bc_api'
db = SQLAlchemy(app)

# Create our database model
class Domain(db.Model):
    __tablename__ = "domains"
    id = db.Column(db.Integer, primary_key=True)
    domain_name = db.Column(db.String, unique=True)
    
    def __init__(self, domain_name):
        self.domain = domain_name

class Mirror(db.Model):
    __tablename__ = "mirrors"
    id = db.Column(db.Integer, primary_key=True)
    mirror_url = db.Column(db.String, unique=True)
    domain_id = db.Column(db.Integer)

    def __init__(self, mirror_url):
        self.mirror_url = mirror_url

class Report(db.Model):
    __tablename__ = "reports"
    id = db.Column(db.Integer, primary_key=True)
    date_reported = db.Column(db.DateTime)
    domain_id = db.Column(db.Integer)
    mirror_id = db.Column(db.Integer)
    location = db.Column(db.String)
    status_code = db.Column(db.Integer)
    browser = db.Column(db.String)
    browser_version = db.Column(db.String)
    ext_version = db.Column(db.String)

    def __init__(self, date_reported):
        self.date_reported = date_reported

