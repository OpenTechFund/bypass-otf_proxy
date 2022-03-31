import datetime

from app import app
from app.extensions import db
from app.models import BridgeConf, Bridge, Group
from app.terraform import BaseAutomation

TEMPLATE = """
terraform {
  required_providers {
    aws = {
      version = "~> 4.2.0"
    }
  }
}

provider "aws" {
  access_key = "{{ aws_access_key }}"
  secret_key = "{{ aws_secret_key }}"
  region = "us-east-1"
}

locals {
  ssh_key = file("{{ ssh_public_key_path }}")
}

{% for group in groups %}
module "label_{{ group.id }}" {
  source  = "cloudposse/label/null"
  version = "0.25.0"
  namespace = "bc"
  tenant = "{{ group.group_name }}"
  label_order = ["namespace", "tenant", "name", "attributes"]
}
{% endfor %}

{% for bridgeconf in bridgeconfs %}
{% for bridge in bridgeconf.bridges %}
{% if not bridge.destroyed %}
module "bridge_{{ bridge.id }}" {
  source = "sr2c/tor-bridge/aws"
  version = "0.0.1"
  ssh_key = local.ssh_key
  contact_info = "hi"
  context = module.label_{{ bridge.conf.group.id }}.context
  name = "bridge"
  attributes = ["{{ bridge.id }}"]
  distribution_method = "{{ bridge.conf.method }}"
}

output "bridge_hashed_fingerprint_{{ bridge.id }}" {
  value = module.bridge_{{ bridge.id }}.hashed_fingerprint
}
{% endif %}
{% endfor %}
{% endfor %}
"""


class BridgeAWSAutomation(BaseAutomation):
    short_name = "bridge_aws"

    def create_missing(self):
        bridgeconfs = BridgeConf.query.filter(
            BridgeConf.provider == "aws"
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
                    bridge.deprecated = datetime.datetime.utcnow()
                    bridge.updated = datetime.datetime.utcnow()
                    active_bridge_count -= 1
                    if active_bridge_count == bridgeconf.number:
                        break
            db.session.commit()

    def destroy_expired(self):
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=0)
        bridges = [b for b in Bridge.query.filter(
            Bridge.destroyed == None,
            Bridge.deprecated < cutoff
        ).all() if b.conf.provider == "aws"]
        for bridge in bridges:
            bridge.destroyed = datetime.datetime.utcnow()
            bridge.updated = datetime.datetime.utcnow()
        db.session.commit()

    def generate_terraform(self):
        self.write_terraform_config(
            TEMPLATE,
            aws_access_key=app.config['AWS_ACCESS_KEY'],
            aws_secret_key=app.config['AWS_SECRET_KEY'],
            ssh_public_key_path=app.config['SSH_PUBLIC_KEY_PATH'],
            groups=Group.query.all(),
            bridgeconfs=BridgeConf.query.filter(
                BridgeConf.destroyed == None,
                BridgeConf.provider == "aws"
            ).all()
        )

    def import_terraform(self):
        outputs = self.terraform_output()
        for output in outputs:
            if output.startswith('bridge_hashed_fingerprint_'):
                bridge = Bridge.query.filter(Bridge.id == output[len('bridge_hashed_fingerprint_'):]).first()
                bridge.hashed_fingerprint = outputs[output]['value'].split(" ")[1]
                bridge.terraform_updated = datetime.datetime.utcnow()
        db.session.commit()


def automate():
    auto = BridgeAWSAutomation()
    auto.destroy_expired()
    auto.create_missing()
    auto.generate_terraform()
    auto.terraform_init()
    auto.terraform_apply()
    auto.import_terraform()


if __name__ == "__main__":
    with app.app_context():
        automate()
