import datetime

from app import app
from app.extensions import db
from app.models import BridgeConf, Bridge, Group
from app.terraform import BaseAutomation

TEMPLATE = """
terraform {
  required_providers {
    random = {
      source = "hashicorp/random"
      version = "3.1.0"
    }
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "1.31.1"
    }
  }
}

provider "hcloud" {
  token = "{{ hcloud_token }}"
}

data "hcloud_datacenters" "ds" {
}

data "hcloud_server_type" "cx11" {
  name = "cx11"
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
resource "random_shuffle" "datacenter_{{ bridge.id }}" {
  input = [for s in data.hcloud_datacenters.ds.datacenters : s.name if contains(s.available_server_type_ids, data.hcloud_server_type.cx11.id)]
  result_count = 1

  lifecycle {
    ignore_changes = [input] # don't replace all the bridges if a new DC appears
  }
}

module "bridge_{{ bridge.id }}" {
  source = "sr2c/tor-bridge/hcloud"
  datacenter = one(random_shuffle.datacenter_{{ bridge.id }}.result)
  name = "bridge"
  attributes = ["{{ bridge.id }}"]
  ssh_key_name = "bc"
  contact_info = "hi"
  distribution_method = "{{ bridge.conf.method }}"
}

output "bridge_hashed_fingerprint_{{ bridge.id }}" {
  value = module.bridge_{{ bridge.id }}.hashed_fingerprint
}
{% endif %}
{% endfor %}
{% endfor %}
"""


class BridgeHcloudAutomation(BaseAutomation):
    short_name = "bridge_hcloud"

    def create_missing(self):
        bridgeconfs = BridgeConf.query.filter(
            BridgeConf.provider == "hcloud"
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
        ).all() if b.conf.provider == "hcloud"]
        for bridge in bridges:
            bridge.destroy()

    def generate_terraform(self):
        self.write_terraform_config(
            TEMPLATE,
            hcloud_token=app.config['HCLOUD_TOKEN'],
            groups=Group.query.all(),
            bridgeconfs=BridgeConf.query.filter(
                BridgeConf.destroyed == None,
                BridgeConf.provider == "hcloud"
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
    auto = BridgeHcloudAutomation()
    auto.destroy_expired()
    auto.create_missing()
    auto.generate_terraform()
    auto.terraform_init()
    auto.terraform_apply()
    auto.import_terraform()


if __name__ == "__main__":
    with app.app_context():
        automate()
