import datetime

from app.extensions import db
from app.models import BridgeConf, Bridge
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

    def import_terraform(self):
        outputs = self.terraform_output()
        for output in outputs:
            if output.startswith('bridge_hashed_fingerprint_'):
                bridge = Bridge.query.filter(Bridge.id == output[len('bridge_hashed_fingerprint_'):]).first()
                bridge.hashed_fingerprint = outputs[output]['value'].split(" ")[1]
                bridge.terraform_updated = datetime.datetime.utcnow()
            if output.startswith('bridge_bridgeline_'):
                bridge = Bridge.query.filter(Bridge.id == output[len('bridge_bridgeline_'):]).first()
                parts = outputs[output]['value'].split(" ")
                del(parts[3])
                bridge.bridgeline = " ".join(parts)
                bridge.terraform_updated = datetime.datetime.utcnow()
        db.session.commit()
