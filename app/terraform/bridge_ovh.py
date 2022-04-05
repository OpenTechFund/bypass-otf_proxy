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
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "~> 1.42.0"
    }
    ovh = {
      source  = "ovh/ovh"
      version = ">= 0.13.0"
    }
  }
}

provider "openstack" {
  auth_url    = "https://auth.cloud.ovh.net/v3/"
  domain_name = "Default" # Domain name - Always at 'default' for OVHcloud
  user_name = "{{ ovh_openstack_user }}"
  password = "{{ ovh_openstack_password }}"
  tenant_id = "{{ ovh_openstack_tenant_id }}"
}

provider "ovh" {
  endpoint           = "ovh-eu"
  application_key    = "{{ ovh_cloud_application_key }}"
  application_secret = "{{ ovh_cloud_application_secret }}"
  consumer_key       = "{{ ovh_cloud_consumer_key }}"
}

data "ovh_cloud_project_regions" "regions" {
  service_name = "{{ ovh_cloud_project_service }}"
  has_services_up = ["instance"]
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
resource "random_shuffle" "region_{{ bridge.id }}" {
  input = data.ovh_cloud_project_regions.regions.names
  result_count = 1

  lifecycle {
    ignore_changes = [input] # don't replace all the bridges if a new region appears
  }
}

module "bridge_{{ bridge.id }}" {
  source = "sr2c/tor-bridge/openstack"
  version = "0.0.4"
  region = one(random_shuffle.region_{{ bridge.id }}.result)
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


class BridgeOvhAutomation(BaseAutomation):
    short_name = "bridge_ovh"

    def create_missing(self):
        bridgeconfs = BridgeConf.query.filter(
            BridgeConf.provider == "ovh"
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
        ).all() if b.conf.provider == "ovh"]
        for bridge in bridges:
            bridge.destroy()

    def generate_terraform(self):
        self.write_terraform_config(
            TEMPLATE,
            ovh_cloud_application_key=app.config['OVH_CLOUD_APPLICATION_KEY'],
            ovh_cloud_application_secret=app.config['OVH_CLOUD_APPLICATION_SECRET'],
            ovh_cloud_consumer_key=app.config['OVH_CLOUD_CONSUMER_KEY'],
            ovh_cloud_project_service=app.config['OVH_CLOUD_PROJECT_SERVICE'],
            ovh_openstack_user=app.config['OVH_OPENSTACK_USER'],
            ovh_openstack_password=app.config['OVH_OPENSTACK_PASSWORD'],
            ovh_openstack_tenant_id=app.config['OVH_OPENSTACK_TENANT_ID'],
            groups=Group.query.all(),
            bridgeconfs=BridgeConf.query.filter(
                BridgeConf.destroyed == None,
                BridgeConf.provider == "ovh"
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
    auto = BridgeOvhAutomation()
    auto.destroy_expired()
    auto.create_missing()
    auto.generate_terraform()
    auto.terraform_init()
    auto.terraform_apply()
    auto.import_terraform()


if __name__ == "__main__":
    with app.app_context():
        automate()
