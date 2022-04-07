import datetime

from app import app
from app.extensions import db
from app.models import BridgeConf, Bridge, Group
from app.terraform import BaseAutomation


class BridgeAutomation(BaseAutomation):
    def create_missing(self):
        bridgeconfs = BridgeConf.query.filter(
            BridgeConf.provider == self.provider
        ).all()
        for bridgeconf in bridgeconfs:
            active_bridges = Bridge.query.filter(
                Bridge.conf_id == bridgeconf.id,
                Bridge.deprecated == None
            ).all()
            if len(active_bridges) < bridgeconf.number:
                for i in range(bridgeconf.number - len(active_bridges)):
                    bridge = Bridge()
                    bridge.conf_id = bridgeconf.id
                    bridge.added = datetime.datetime.utcnow()
                    bridge.updated = datetime.datetime.utcnow()
                    db.session.add(bridge)
            elif len(active_bridges) > bridgeconf.number:
                active_bridge_count = len(active_bridges)
                for bridge in active_bridges:
                    bridge.deprecate()
                    active_bridge_count -= 1
                    if active_bridge_count == bridgeconf.number:
                        break

    def destroy_expired(self):
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=0)
        bridges = [b for b in Bridge.query.filter(
            Bridge.destroyed == None,
            Bridge.deprecated < cutoff
        ).all() if b.conf.provider == self.provider]
        for bridge in bridges:
            bridge.destroy()

    def generate_terraform(self):
        self.write_terraform_config(
            self.template,
            groups=Group.query.all(),
            bridgeconfs=BridgeConf.query.filter(
                BridgeConf.destroyed == None,
                BridgeConf.provider == self.provider
            ).all(),
            global_namespace=app.config['GLOBAL_NAMESPACE'],
            **{
                k: app.config[k.upper()]
                for k in self.template_parameters
            }
        )

    def import_terraform(self):
        outputs = self.terraform_output()
        for output in outputs:
            if output.startswith('bridge_hashed_fingerprint_'):
                parts = outputs[output]['value'].split(" ")
                if len(parts) < 2:
                    continue
                bridge = Bridge.query.filter(Bridge.id == output[len('bridge_hashed_fingerprint_'):]).first()
                bridge.nickname = parts[0]
                bridge.hashed_fingerprint = parts[1]
                bridge.terraform_updated = datetime.datetime.utcnow()
            if output.startswith('bridge_bridgeline_'):
                parts = outputs[output]['value'].split(" ")
                if len(parts) < 4:
                    continue
                bridge = Bridge.query.filter(Bridge.id == output[len('bridge_bridgeline_'):]).first()
                del(parts[3])
                bridge.bridgeline = " ".join(parts)
                bridge.terraform_updated = datetime.datetime.utcnow()
        db.session.commit()