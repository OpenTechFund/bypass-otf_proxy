"""
Models for BC API
"""
from app import db

# Create our database model
class Domain(db.Model):
    __tablename__ = "domains"
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String, unique=True)
    
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
