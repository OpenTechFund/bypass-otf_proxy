from app import app
from app.models import BridgeConf, Group
from app.terraform.bridge import BridgeAutomation

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

output "bridge_bridgeline_{{ bridge.id }}" {
  value = module.bridge_{{ bridge.id }}.bridgeline
}
{% endif %}
{% endfor %}
{% endfor %}
"""


class BridgeAWSAutomation(BridgeAutomation):
    short_name = "bridge_aws"
    provider = "aws"

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
