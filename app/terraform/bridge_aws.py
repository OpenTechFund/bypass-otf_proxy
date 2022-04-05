from app import app
from app.terraform.bridge import BridgeAutomation


class BridgeAWSAutomation(BridgeAutomation):
    short_name = "bridge_aws"
    provider = "aws"

    template_parameters = [
        "aws_access_key",
        "aws_secret_key",
        "ssh_public_key_path"
    ]

    template = """
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
      namespace = "{{ global_namespace }}"
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
      context = module.label_{{ bridgeconf.group.id }}.context
      name = "br"
      attributes = ["{{ bridge.id }}"]
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
