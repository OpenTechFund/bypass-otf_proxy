from app import app
from app.models import Group
from app.terraform import BaseAutomation


class EotkAutomation(BaseAutomation):
    short_name = "eotk"

    template_parameters = [
        "aws_access_key",
        "aws_secret_key"
    ]

    template = """
    terraform {
      required_providers {
        aws = {
          version = "~> 4.4.0"
        }
      }
    }
    
    provider "aws" {
      access_key = "{{ aws_access_key }}"
      secret_key = "{{ aws_secret_key }}"
      region = "us-east-1"
    }
    
    {% for group in groups %}
    module "label_{{ group.id }}" {
      source  = "cloudposse/label/null"
      version = "0.25.0"
      namespace = "{{ global_namespace }}"
      tenant = "{{ group.group_name }}"
      label_order = ["namespace", "tenant", "name", "attributes"]
    }
    
    module "log_bucket_{{ group.id }}" {
      source = "cloudposse/s3-log-storage/aws"
      version = "0.28.0"
      context = module.label_{{ group.id }}.context
      name = "logs"
      attributes = ["eotk"]
      acl                      = "log-delivery-write"
      standard_transition_days = 30
      glacier_transition_days  = 60
      expiration_days          = 90
    }
    
    resource "aws_sns_topic" "alarms_{{ group.id }}" {
      name = "${module.label_{{ group.id }}.id}-eotk-alarms"
    }
    {% endfor %}
    """

    def generate_terraform(self):
        self.write_terraform_config(
            self.template,
            groups=Group.query.filter(Group.eotk == True).all(),
            global_namespace=app.config['GLOBAL_NAMESPACE'],
            **{
                k: app.config[k.upper()]
                for k in self.template_parameters
            }
        )


if __name__ == "__main__":
    with app.app_context():
        auto = EotkAutomation()
        auto.generate_terraform()
        auto.terraform_init()
        #auto.terraform_apply()
