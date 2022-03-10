import json
import os
import subprocess

import jinja2

from app import app
from app.extensions import db
from app.models import Proxy, Group
from app.terraform import terraform_init, terraform_apply

TEMPLATE = """
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
  namespace = "bc"
  tenant = "{{ group.group_name }}"
  label_order = ["namespace", "tenant", "name", "attributes"]
}

module "log_bucket_{{ group.id }}" {
  source = "cloudposse/s3-log-storage/aws"
  version = "0.28.0"
  context = module.label_{{ group.id }}.context
  name = "logs"
  attributes = ["cloudfront"]
  acl                      = "log-delivery-write"
  standard_transition_days = 30
  glacier_transition_days  = 60
  expiration_days          = 90
}
{% endfor %}

{% for proxy in proxies %}
module "cloudfront_{{ proxy.id }}" {
  source = "sr2c/bc-proxy/aws"
  version = "0.0.1"
  origin_domain = "{{ proxy.origin.domain_name }}"
  logging_bucket = module.log_bucket_{{ proxy.origin.group.id }}.bucket_domain_name
  context = module.label_{{ proxy.origin.group.id }}.context
  name = "proxy"
  attributes = ["{{ proxy.origin.domain_name }}"]
}
{% endfor %}
"""


def generate_terraform():
    filename = os.path.join(
        app.config['TERRAFORM_DIRECTORY'],
        'cloudfront',
        'main.tf'
    )
    tmpl = jinja2.Template(TEMPLATE)
    rendered = tmpl.render(
        aws_access_key=app.config['AWS_ACCESS_KEY'],
        aws_secret_key=app.config['AWS_SECRET_KEY'],
        groups=Group.query.all(),
        proxies=Proxy.query.filter(
            Proxy.provider == 'cloudfront',
            Proxy.destroyed == None
        ).all()
    )
    with open(filename, 'w') as out:
        out.write(rendered)


def import_cloudfront_values():
    terraform = subprocess.run(
        ['terraform', 'show', '-json'],
        cwd=os.path.join(
            app.config['TERRAFORM_DIRECTORY'],
            "cloudfront"),
        stdout=subprocess.PIPE)
    state = json.loads(terraform.stdout)

    for mod in state['values']['root_module']['child_modules']:
        if mod['address'].startswith('module.cloudfront_'):
            for res in mod['resources']:
                if res['address'].endswith('aws_cloudfront_distribution.this'):
                    proxy = Proxy.query.filter(Proxy.id == mod['address'][len('module.cloudfront_'):]).first()
                    proxy.url = "https://" + res['values']['domain_name']
                    db.session.commit()
                    break


if __name__ == "__main__":
    db.init_app(app)
    with app.app_context():
        generate_terraform()
        terraform_init("cloudfront")
        terraform_apply("cloudfront")
        import_cloudfront_values()
