from app import app
from app.terraform.bridge import BridgeAutomation


class BridgeGandiAutomation(BridgeAutomation):
    short_name = "bridge_gandi"
    provider = "gandi"

    template_parameters = [
        "gandi_openstack_user",
        "gandi_openstack_password",
        "gandi_openstack_tenant_name",
        "ssh_public_key_path"
    ]

    template = """
    terraform {
      required_providers {
        openstack = {
          source  = "terraform-provider-openstack/openstack"
          version = "~> 1.42.0"
        }
      }
    }

    provider "openstack" {
      auth_url = "https://keystone.sd6.api.gandi.net:5000/v3"
      user_domain_name = "public"
      project_domain_name = "public"
      user_name = "{{ gandi_openstack_user }}"
      password = "{{ gandi_openstack_password }}"
      tenant_name = "{{ gandi_openstack_tenant_name }}"
      region = "FR-SD6"
    }

    locals {
      ssh_key = file("{{ ssh_public_key_path }}")
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
    module "bridge_{{ bridge.id }}" {
      source = "sr2c/tor-bridge/openstack"
      version = "0.0.6"
      context = module.label_{{ bridgeconf.group.id }}.context
      name = "br"
      attributes = ["{{ bridge.id }}"]
      ssh_key = local.ssh_key
      contact_info = "hi"
      distribution_method = "{{ bridge.conf.method }}"

      image_name = "Debian 11 Bullseye"
      flavor_name = "V-R1"
      external_network_name = "public"
      require_block_device_creation = true
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
    auto = BridgeGandiAutomation()
    auto.destroy_expired()
    auto.create_missing()
    auto.generate_terraform()
    auto.terraform_init()
    auto.terraform_apply()
    auto.import_terraform()


if __name__ == "__main__":
    with app.app_context():
        automate()
