import datetime
import json
import os
import subprocess

import boto3
import jinja2

from app import app
from app.extensions import db
from app.models import Proxy, Group, Origin, ProxyAlarm, ProxyAlarmState
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

resource "aws_sns_topic" "alarms_{{ group.id }}" {
  name = "${module.label_{{ group.id }}.id}-cloudfront-alarms"
}
{% endfor %}

{% for proxy in proxies %}
module "cloudfront_{{ proxy.id }}" {
  source = "sr2c/bc-proxy/aws"
  version = "0.0.5"
  origin_domain = "{{ proxy.origin.domain_name }}"
  logging_bucket = module.log_bucket_{{ proxy.origin.group.id }}.bucket_domain_name
  sns_topic_arn = aws_sns_topic.alarms_{{ proxy.origin.group.id }}.arn
  low_bandwidth_alarm = false
  context = module.label_{{ proxy.origin.group.id }}.context
  name = "proxy"
  attributes = ["{{ proxy.origin.domain_name }}"]
}
{% endfor %}
"""


def create_missing_proxies():
    with app.app_context():
        origins = Origin.query.all()
        for origin in origins:
            cloudfront_proxies = [
                x for x in origin.proxies
                if x.provider == "cloudfront" and x.deprecated is None and x.destroyed is None
            ]
            if not cloudfront_proxies:
                proxy = Proxy()
                proxy.origin_id = origin.id
                proxy.provider = "cloudfront"
                proxy.added = datetime.datetime.utcnow()
                proxy.updated = datetime.datetime.utcnow()
                db.session.add(proxy)
                db.session.commit()


def destroy_expired_proxies():
    with app.app_context():
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=3)
        proxies = Proxy.query.filter(
            Proxy.destroyed == None,
            Proxy.deprecated < cutoff
        ).all()
        for proxy in proxies:
            proxy.destroyed = datetime.datetime.utcnow()
            proxy.updated = datetime.datetime.utcnow()
        db.session.commit()


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
                    proxy.slug = res['values']['id']
                    proxy.terraform_updated = datetime.datetime.utcnow()
                    db.session.commit()
                    break


def import_cloudwatch_alarms():
    cloudwatch = boto3.client('cloudwatch',
                              aws_access_key_id=app.config['AWS_ACCESS_KEY'],
                              aws_secret_access_key=app.config['AWS_SECRET_KEY'],
                              region_name='us-east-1')
    dist_paginator = cloudwatch.get_paginator('describe_alarms')
    page_iterator = dist_paginator.paginate(AlarmNamePrefix="bandwidth-out-high-")
    for page in page_iterator:
        for alarm in page['MetricAlarms']:
            dist_id = alarm["AlarmName"][len("bandwidth-out-high-"):]
            proxy = Proxy.query.filter(Proxy.slug == dist_id).first()
            if proxy is None:
                print("Skipping unknown proxy " + dist_id)
                continue
            proxy_alarm = ProxyAlarm.query.filter(
                ProxyAlarm.proxy_id == proxy.id,
                ProxyAlarm.alarm_type == "bandwidth-out-high"
            ).first()
            if proxy_alarm is None:
                proxy_alarm = ProxyAlarm()
                proxy_alarm.proxy_id = proxy.id
                proxy_alarm.alarm_type = "bandwidth-out-high"
                proxy_alarm.state_changed = datetime.datetime.utcnow()
                db.session.add(proxy_alarm)
            proxy_alarm.last_updated = datetime.datetime.utcnow()
            old_state = proxy_alarm.alarm_state
            if alarm['StateValue'] == "OK":
                proxy_alarm.alarm_state = ProxyAlarmState.OK
            elif alarm['StateValue'] == "ALARM":
                proxy_alarm.alarm_state = ProxyAlarmState.CRITICAL
            else:
                proxy_alarm.alarm_state = ProxyAlarmState.UNKNOWN
            if proxy_alarm.alarm_state != old_state:
                proxy_alarm.state_changed = datetime.datetime.utcnow()
        db.session.commit()


if __name__ == "__main__":
    db.init_app(app)
    with app.app_context():
        destroy_expired_proxies()
        create_missing_proxies()
        generate_terraform()
        terraform_init("cloudfront")
        terraform_apply("cloudfront")
        import_cloudfront_values()
        import_cloudwatch_alarms()
