import datetime
import json
import os
import subprocess

import boto3

from app import app
from app.extensions import db
from app.models import Proxy, Alarm, AlarmState
from app.terraform.proxy import ProxyAutomation


class ProxyCloudfrontAutomation(ProxyAutomation):
    short_name = "proxy_cloudfront"
    provider = "cloudfront"

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


def import_cloudfront_values():
    terraform = subprocess.run(
        ['terraform', 'show', '-json'],
        cwd=os.path.join(
            app.config['TERRAFORM_DIRECTORY'],
            "proxy_cloudfront"),
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
        for cw_alarm in page['MetricAlarms']:
            dist_id = cw_alarm["AlarmName"][len("bandwidth-out-high-"):]
            proxy = Proxy.query.filter(Proxy.slug == dist_id).first()
            if proxy is None:
                print("Skipping unknown proxy " + dist_id)
                continue
            alarm = Alarm.query.filter(
                Alarm.proxy_id == proxy.id,
                Alarm.alarm_type == "bandwidth-out-high"
            ).first()
            if alarm is None:
                alarm = Alarm()
                alarm.target = "proxy"
                alarm.proxy_id = proxy.id
                alarm.alarm_type = "bandwidth-out-high"
                alarm.state_changed = datetime.datetime.utcnow()
                db.session.add(alarm)
            alarm.last_updated = datetime.datetime.utcnow()
            old_state = alarm.alarm_state
            if cw_alarm['StateValue'] == "OK":
                alarm.alarm_state = AlarmState.OK
            elif cw_alarm['StateValue'] == "ALARM":
                alarm.alarm_state = AlarmState.CRITICAL
            else:
                alarm.alarm_state = AlarmState.UNKNOWN
            if alarm.alarm_state != old_state:
                alarm.state_changed = datetime.datetime.utcnow()
        db.session.commit()
    alarm = Alarm.query.filter(
        Alarm.proxy_id == None,
        Alarm.alarm_type == "cloudfront-quota"
    ).first()
    if alarm is None:
        alarm = Alarm()
        alarm.target = "service/cloudfront"
        alarm.alarm_type = "cloudfront-quota"
        alarm.state_changed = datetime.datetime.utcnow()
        db.session.add(alarm)
    alarm.last_updated = datetime.datetime.utcnow()
    deployed_count = len(Proxy.query.filter(
        Proxy.destroyed == None).all())
    old_state = alarm.alarm_state
    if deployed_count > 370:
        alarm.alarm_state = AlarmState.CRITICAL
    elif deployed_count > 320:
        alarm.alarm_state = AlarmState.WARNING
    else:
        alarm.alarm_state = AlarmState.OK
    if alarm.alarm_state != old_state:
        alarm.state_changed = datetime.datetime.utcnow()
    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        auto = ProxyCloudfrontAutomation()
        auto.destroy_expired_proxies()
        auto.create_missing_proxies()
        auto.generate_terraform()
        auto.terraform_init()
        auto.terraform_apply()
        import_cloudfront_values()
        import_cloudwatch_alarms()
