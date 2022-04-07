from app import app
from app.terraform.bridge import BridgeAutomation


class BridgeHcloudAutomation(BridgeAutomation):
    short_name = "bridge_hcloud"
    provider = "hcloud"

    template_parameters = [
        "hcloud_token"
    ]

    template = """
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
      namespace = "{{ global_namespace }}"
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
      version = "0.0.2"
      datacenter = one(random_shuffle.datacenter_{{ bridge.id }}.result)
      context = module.label_{{ bridgeconf.group.id }}.context
      name = "br"
      attributes = ["{{ bridge.id }}"]
      ssh_key_name = "bc"
      contact_info = "hi"
      distribution_method = "{{ bridge.conf.method }}"
    }

    output "bridge_hashed_fingerprint_{{ bridge.id }}" {
      value = module.bridge_{{ bridge.id }}.hashed_fingerprint
    }

    output "bridge_bridgeline_{{ bridge.id }}" {
      value = module.bridge_{{ bridge.id }}.bridgeline
      sensitive = true
    }
    {% endif %}
    {% endfor %}
    {% endfor %}
    """


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