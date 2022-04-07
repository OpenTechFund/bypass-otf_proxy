import enum
from datetime import datetime

from app.extensions import db


class AbstractResource(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    added = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)
    updated = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)
    deprecated = db.Column(db.DateTime(), nullable=True)
    destroyed = db.Column(db.DateTime(), nullable=True)

    def deprecate(self):
        self.deprecated = datetime.utcnow()
        self.updated = datetime.utcnow()
        db.session.commit()

    def destroy(self):
        if self.deprecated is None:
            self.deprecated = datetime.utcnow()
        self.destroyed = datetime.utcnow()
        self.updated = datetime.utcnow()
        db.session.commit()

    def __repr__(self):
        return f"<{self.__class__.__name__} #{self.id}>"


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    eotk = db.Column(db.Boolean())
    added = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)
    updated = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)

    origins = db.relationship("Origin", back_populates="group")
    bridgeconfs = db.relationship("BridgeConf", back_populates="group")
    alarms = db.relationship("Alarm", back_populates="group")

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
    destroyed = db.Column(db.DateTime(), nullable=True)

    group = db.relationship("Group", back_populates="origins")
    mirrors = db.relationship("Mirror", back_populates="origin")
    proxies = db.relationship("Proxy", back_populates="origin")
    alarms = db.relationship("Alarm", back_populates="origin")

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


class Proxy(AbstractResource):
    id = db.Column(db.Integer, primary_key=True)
    origin_id = db.Column(db.Integer, db.ForeignKey("origin.id"), nullable=False)
    provider = db.Column(db.String(20), nullable=False)
    slug = db.Column(db.String(20), nullable=True)
    terraform_updated = db.Column(db.DateTime(), nullable=True)
    url = db.Column(db.String(255), nullable=True)

    origin = db.relationship("Origin", back_populates="proxies")
    alarms = db.relationship("Alarm", back_populates="proxy")

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


class AlarmState(enum.Enum):
    UNKNOWN = 0
    OK = 1
    WARNING = 2
    CRITICAL = 3


class Alarm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target = db.Column(db.String(60), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"))
    origin_id = db.Column(db.Integer, db.ForeignKey("origin.id"))
    proxy_id = db.Column(db.Integer, db.ForeignKey("proxy.id"))
    bridge_id = db.Column(db.Integer, db.ForeignKey("bridge.id"))
    alarm_type = db.Column(db.String(255), nullable=False)
    alarm_state = db.Column(db.Enum(AlarmState), default=AlarmState.UNKNOWN, nullable=False)
    state_changed = db.Column(db.DateTime(), nullable=False)
    last_updated = db.Column(db.DateTime())
    text = db.Column(db.String(255))

    group = db.relationship("Group", back_populates="alarms")
    origin = db.relationship("Origin", back_populates="alarms")
    proxy = db.relationship("Proxy", back_populates="alarms")
    bridge = db.relationship("Bridge", back_populates="alarms")

    def update_state(self, state: AlarmState, text: str):
        if self.state != state:
            self.state_changed = datetime.utcnow()
        self.alarm_state = state
        self.text = text
        self.last_updated = datetime.utcnow()
        db.session.commit()


class BridgeConf(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    provider = db.Column(db.String(20), nullable=False)
    method = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(255))
    number = db.Column(db.Integer())
    added = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)
    updated = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)
    destroyed = db.Column(db.DateTime(), nullable=True)

    group = db.relationship("Group", back_populates="bridgeconfs")
    bridges = db.relationship("Bridge", back_populates="conf")

    def destroy(self):
        self.destroyed = datetime.utcnow()
        self.updated = datetime.utcnow()
        for bridge in self.bridges:
            if bridge.destroyed is None:
                bridge.destroyed = datetime.utcnow()
                bridge.updated = datetime.utcnow()
        db.session.commit()


class Bridge(AbstractResource):
    conf_id = db.Column(db.Integer, db.ForeignKey("bridge_conf.id"), nullable=False)
    terraform_updated = db.Column(db.DateTime(), nullable=True)
    nickname = db.Column(db.String(255), nullable=True)
    fingerprint = db.Column(db.String(255), nullable=True)
    hashed_fingerprint = db.Column(db.String(255), nullable=True)
    bridgeline = db.Column(db.String(255), nullable=True)

    conf = db.relationship("BridgeConf", back_populates="bridges")
    alarms = db.relationship("Alarm", back_populates="bridge")


class MirrorList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    format = db.Column(db.String(20), nullable=False)
    container = db.Column(db.String(255), nullable=False)
    branch = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    added = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)
    updated = db.Column(db.DateTime(), default=datetime.utcnow(), nullable=False)
    deprecated = db.Column(db.DateTime(), nullable=True)
    destroyed = db.Column(db.DateTime(), nullable=True)

    def destroy(self):
        self.destroyed = datetime.utcnow()
        self.updated = datetime.utcnow()
        db.session.commit()

    def url(self):
        if self.provider == "gitlab":
            return f"https://gitlab.com/{self.container}/-/raw/{self.branch}/{self.filename}"
        if self.provider == "github":
            return f"https://raw.githubusercontent.com/{self.container}/{self.branch}/{self.filename}"
        if self.provider == "s3":
            return f"s3://{self.container}/{self.filename}"
