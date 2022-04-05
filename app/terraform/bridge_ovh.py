from app import app
from app.terraform.bridge import BridgeAutomation


class BridgeOvhAutomation(BridgeAutomation):
    short_name = "bridge_ovh"
    provider = "ovh"

    template_parameters = [
        "ovh_cloud_application_key",
        "ovh_cloud_application_secret",
        "ovh_cloud_consumer_key",
        "ovh_cloud_project_service",
        "ovh_openstack_user",
        "ovh_openstack_password",
        "ovh_openstack_tenant_id",
        "ssh_public_key_path"
    ]

    template = """
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
      namespace = "{{ global_namespace }}"
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
      context = module.label_{{ group.id }}.context
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
      sensitive = true
    }
    {% endif %}
    {% endfor %}
    {% endfor %}
    """


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
