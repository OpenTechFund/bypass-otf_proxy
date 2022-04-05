from app import app
from app.models import BridgeConf, Group
from app.terraform.bridge import BridgeAutomation

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

locals {
  ssh_key = file("{{ ssh_public_key_path }}")
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
  ssh_key = local.ssh_key
  contact_info = "hi"
  distribution_method = "{{ bridge.conf.method }}"
}

output "bridge_hashed_fingerprint_{{ bridge.id }}" {
  value = module.bridge_{{ bridge.id }}.hashed_fingerprint
}

output "bridge_bridgeline_{{ bridge.id }}" {
  value = module.bridge_{{ bridge.id }}.bridgeline
}
{% endif %}
{% endfor %}
{% endfor %}
"""


class BridgeOvhAutomation(BridgeAutomation):
    short_name = "bridge_ovh"
    provider = "ovh"

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
            ssh_public_key_path=app.config['SSH_PUBLIC_KEY_PATH'],
            groups=Group.query.all(),
            bridgeconfs=BridgeConf.query.filter(
                BridgeConf.destroyed == None,
                BridgeConf.provider == self.provider
            ).all()
        )


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
