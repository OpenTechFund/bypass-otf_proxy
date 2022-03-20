import enum
from datetime import datetime

from app.extensions import db


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    eotk = db.Column(db.Boolean())
    added = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)
    updated = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)

    origins = db.relationship("Origin", back_populates="group")

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.group_name,
            "description": self.description,
            "added": self.added,
            "updated": self.updated
        }

    def __repr__(self):
        return '<Group %r>' % self.group_name


class Origin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    domain_name = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    added = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)
    updated = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)

    group = db.relationship("Group", back_populates="origins")
    mirrors = db.relationship("Mirror", back_populates="origin")
    proxies = db.relationship("Proxy", back_populates="origin")

    def as_dict(self):
        return {
            "id": self.id,
            "group_id": self.group.id,
            "group_name": self.group.group_name,
            "domain_name": self.domain_name,
            "description": self.description,
            "added": self.added,
            "updated": self.updated
        }

    def __repr__(self):
        return '<Origin %r>' % self.domain_name


class Proxy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    origin_id = db.Column(db.Integer, db.ForeignKey("origin.id"), nullable=False)
    provider = db.Column(db.String(20), nullable=False)
    slug = db.Column(db.String(20), nullable=True)
    added = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)
    updated = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)
    deprecated = db.Column(db.DateTime(), nullable=True)
    destroyed = db.Column(db.DateTime(), nullable=True)
    terraform_updated = db.Column(db.DateTime(), nullable=True)
    url = db.Column(db.String(255), nullable=True)

    origin = db.relationship("Origin", back_populates="proxies")
    alarms = db.relationship("ProxyAlarm", back_populates="proxy")

    def as_dict(self):
        return {
            "id": self.id,
            "origin_id": self.origin.id,
            "origin_domain_name": self.origin.domain_name,
            "provider": self.provider,
            "slug": self.slug,
            "added": self.added,
            "updated": self.updated
        }

    def deprecate(self):
        self.deprecated = datetime.utcnow()
        self.updated = datetime.utcnow()
        db.session.commit()

    def __repr__(self):
        return '<Proxy %r_%r>' % (self.origin.domain_name, self.id)


class Mirror(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    origin_id = db.Column(db.Integer, db.ForeignKey("origin.id"), nullable=False)
    url = db.Column(db.String(255), unique=True, nullable=False)
    added = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)
    updated = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)
    deprecated = db.Column(db.DateTime(), nullable=True)
    destroyed = db.Column(db.DateTime(), nullable=True)

    origin = db.relationship("Origin", back_populates="mirrors")

    def as_dict(self):
        return {
            "id": self.id,
            "origin_id": self.origin_id,
            "origin_domain_name": self.origin.domain_name,
            "url": self.url,
            "added": self.added,
            "updated": self.updated
        }

    def __repr__(self):
        return '<Mirror %r_%r>' % (self.origin.domain_name, self.id)


class ProxyAlarmState(enum.Enum):
    UNKNOWN = 0
    OK = 1
    WARNING = 2
    CRITICAL = 3


class ProxyAlarm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    proxy_id = db.Column(db.Integer, db.ForeignKey("proxy.id"), nullable=False)
    alarm_type = db.Column(db.String(255), nullable=False)
    alarm_state = db.Column(db.Enum(ProxyAlarmState), default=ProxyAlarmState.UNKNOWN, nullable=False)
    state_changed = db.Column(db.DateTime(), nullable=False)
    last_updated = db.Column(db.DateTime())

    proxy = db.relationship("Proxy", back_populates="alarms")
