import datetime

from app import app
from app.extensions import db
from app.models import Group, Origin, Proxy
from app.terraform import BaseAutomation


class ProxyAutomation(BaseAutomation):
    def create_missing_proxies(self):
        origins = Origin.query.all()
        for origin in origins:
            cloudfront_proxies = [
                x for x in origin.proxies
                if x.provider == self.provider and x.deprecated is None and x.destroyed is None
            ]
            if not cloudfront_proxies:
                proxy = Proxy()
                proxy.origin_id = origin.id
                proxy.provider = self.provider
                proxy.added = datetime.datetime.utcnow()
                proxy.updated = datetime.datetime.utcnow()
                db.session.add(proxy)
                db.session.commit()

    def destroy_expired_proxies(self):
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=3)
        proxies = Proxy.query.filter(
            Proxy.destroyed == None,
            Proxy.provider == self.provider,
            Proxy.deprecated < cutoff
        ).all()
        for proxy in proxies:
            proxy.destroyed = datetime.datetime.utcnow()
            proxy.updated = datetime.datetime.utcnow()
        db.session.commit()

    def generate_terraform(self):
        self.write_terraform_config(
            self.template,
            groups=Group.query.all(),
            proxies=Proxy.query.filter(
                Proxy.provider == self.provider,
                Proxy.destroyed == None
            ).all(),
            global_namespace=app.config['GLOBAL_NAMESPACE'],
            **{
                k: app.config[k.upper()]
                for k in self.template_parameters
            }
        )
