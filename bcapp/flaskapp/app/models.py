"""
Models for BC API
"""
from flask_login import UserMixin
from app import db

# Create our database model
class Domain(db.Model):
    __tablename__ = "domains"
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String, unique=True)
    paths_ignore = db.Column(db.String)
    ext_ignore = db.Column(db.String)
    s3_storage_bucket = db.Column(db.String)
    
    def __repr__(self):
        return '<id {}>'.format(self.id)

class DomainGroup(db.Model):
    __tablename__ = "domain_groups"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)

    def __repr__(self):
        return '<id {}>'.format(self.id)

class DGDomain(db.Model):
    __tablename__ = "dg_domains"
    id = db.Column(db.Integer, primary_key=True)
    domain_group_id = db.Column(db.Integer)
    domain_id = db.Column(db.Integer)

class Onion(db.Model):
    __tablename__ = "onions"
    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer)
    onion = db.Column(db.String, unique=True)

    def __repr__(self):
        return '<id {}>'.format(self.id)

class OnionReport(db.Model):
    __tablename__ = "onion_reports"
    id = db.Column(db.Integer, primary_key=True)
    onion_id = db.Column(db.Integer)
    domain_id = db.Column(db.Integer)
    date_reported = db.Column(db.DateTime)
    onion_status = db.Column(db.Integer)
    user_agent = db.Column(db.String)

    def __repr__(self):
        return '<id {}>'.format(self.id)

class Mirror(db.Model):
    __tablename__ = "mirrors"
    id = db.Column(db.Integer, primary_key=True)
    mirror_url = db.Column(db.String, unique=True)
    domain_id = db.Column(db.Integer)

    def __repr__(self):
        return '<id {}>'.format(self.id)

class Report(db.Model):
    __tablename__ = "reports"
    id = db.Column(db.Integer, primary_key=True)
    auth_token = db.Column(db.String)
    date_reported = db.Column(db.DateTime)
    domain_id = db.Column(db.Integer)
    mirror_id = db.Column(db.Integer)
    domain_status = db.Column(db.Integer)
    domain_content = db.Column(db.String)
    mirror_status = db.Column(db.Integer)
    mirror_content = db.Column(db.String)
    user_agent = db.Column(db.String)
    ext_version = db.Column(db.String)
    ext_uuid = db.Column(db.String)
    ip = db.Column(db.String)
    latitude = db.Column(db.Numeric)
    longitude = db.Column(db.Numeric)
    accuracy = db.Column(db.Numeric)
    
    def __repr__(self):
        return '<id {}>'.format(self.id)

class Token(db.Model):
    __tablename__ = "auth_tokens"
    id = db.Column(db.Integer, primary_key=True)
    auth_token = db.Column(db.String)

    def __repr__(self):
        return '<id {}>'.format(self.id)

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password = db.Column(db.String(128))
    name = db.Column(db.String(120))
    domain_group_id = db.Column(db.String(120))
    admin = db.Column(db.Boolean)
    active = db.Column(db.Boolean)

    def __repr__(self):
        return '<id {}>'.format(self.id)

class LogReport(db.Model):
    __tablename__ = "log_reports"
    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer)
    date_of_report = db.Column(db.DateTime)
    first_date_of_log = db.Column(db.DateTime)
    last_date_of_log = db.Column(db.DateTime)
    hits = db.Column(db.Numeric)
    report = db.Column(db.String)
    log_type = db.Column(db.String)

    def __repr__(self):
        return '<id {}>'.format(self.id)