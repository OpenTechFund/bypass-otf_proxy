import datetime
import string
import random

from azure.identity import ClientSecretCredential
from azure.mgmt.alertsmanagement import AlertsManagementClient
import tldextract

from app import app
from app.alarms import get_proxy_alarm
from app.extensions import db
from app.models import Group, Proxy, Alarm, AlarmState
from app.terraform.proxy import ProxyAutomation


class ProxyAzureCdnAutomation(ProxyAutomation):
    short_name = "proxy_azure_cdn"
    provider = "azure_cdn"

    template_parameters = [
        "azure_resource_group_name",
        "azure_storage_account_name",
        "azure_location",
        "azure_client_id",
        "azure_client_secret",
        "azure_subscription_id",
        "azure_tenant_id"
    ]

    template = """
    terraform {
      required_providers {
        azurerm = {
          source  = "hashicorp/azurerm"
          version = "=2.99.0"
        }
      }
    }
    
    provider "azurerm" {
      features {}
      
      client_id = "{{ azure_client_id }}"
      client_secret = "{{ azure_client_secret }}"
      subscription_id = "{{ azure_subscription_id }}"
      tenant_id = "{{ azure_tenant_id }}"
      skip_provider_registration = true
    }
    
    data "azurerm_resource_group" "this" {
      name = "{{ azure_resource_group_name }}"
    }
    
    resource "azurerm_storage_account" "this" {
      name                     = "{{ azure_storage_account_name }}"
      resource_group_name      = data.azurerm_resource_group.this.name
      location                 = "{{ azure_location }}"
      account_tier             = "Standard"
      account_replication_type = "RAGRS"
    }
    
    {% for group in groups %}
    module "label_{{ group.id }}" {
      source  = "cloudposse/label/null"
      version = "0.25.0"
      namespace = "{{ global_namespace }}"
      tenant = "{{ group.group_name }}"
      label_order = ["namespace", "tenant", "name", "attributes"]
    }
    
    resource "azurerm_cdn_profile" "profile_{{ group.id }}" {
      name                = module.label_{{ group.id }}.id
      location            = "{{ azure_location }}"
      resource_group_name = data.azurerm_resource_group.this.name
      sku                 = "Standard_Microsoft"
    
      tags = module.label_{{ group.id }}.tags
    }
    
    resource "azurerm_monitor_diagnostic_setting" "profile_diagnostic_{{ group.id }}" {
      name               = "cdn-diagnostics"
      target_resource_id = azurerm_cdn_profile.profile_{{ group.id }}.id
      storage_account_id = azurerm_storage_account.this.id
    
      log {
        category = "AzureCDNAccessLog"
        enabled  = true
    
        retention_policy {
          enabled = true
          days = 90
        }
      }
      
      metric {
        category = "AllMetrics"
        enabled  = true
    
        retention_policy {
          enabled = true
          days = 90
        }
      }
    }
    
    resource "azurerm_monitor_metric_alert" "response_alert_{{ group.id }}" {
      name                = "bandwidth-out-high-${module.label_{{ group.id }}.id}"
      resource_group_name = data.azurerm_resource_group.this.name
      scopes              = [azurerm_cdn_profile.profile_{{ group.id }}.id]
      description         = "Action will be triggered when response size is too high."
    
      criteria {
        metric_namespace = "Microsoft.Cdn/profiles"
        metric_name      = "ResponseSize"
        aggregation      = "Total"
        operator         = "GreaterThan"
        threshold        = 21474836481
      }
      
      window_size = "PT1H"
    }
    {% endfor %}
    
    {% for proxy in proxies %}
    resource "azurerm_cdn_endpoint" "endpoint_{{ proxy.id }}" {
      name                = "{{ proxy.slug }}"
      profile_name        = azurerm_cdn_profile.profile_{{ proxy.origin.group.id }}.name
      location            = "{{ azure_location }}"
      resource_group_name = data.azurerm_resource_group.this.name
    
      origin {
        name      = "upstream"
        host_name = "{{ proxy.origin.domain_name }}"
      }
    
      global_delivery_rule {
        modify_request_header_action {
          action = "Overwrite"
          name = "User-Agent"
          value = "Amazon CloudFront"
        }
        modify_request_header_action {
          action = "Append"
          name = "X-Amz-Cf-Id"
          value = "dummystring"
        }
      }
    }
    
    resource "azurerm_monitor_diagnostic_setting" "diagnostic_{{ proxy.id }}" {
      name               = "cdn-diagnostics"
      target_resource_id = azurerm_cdn_endpoint.endpoint_{{ proxy.id }}.id
      storage_account_id = azurerm_storage_account.this.id
    
      log {
        category = "CoreAnalytics"
        enabled  = true
    
        retention_policy {
          enabled = true
          days = 90
        }
      }
    }
    {% endfor %}
    """

    def create_missing_proxies(self):
        groups = Group.query.all()
        for group in groups:
            active_proxies = len([p for p in Proxy.query.filter(
                Proxy.provider == 'azure_cdn',
                Proxy.destroyed == None
            ).all() if p.origin.group_id == group.id])
            for origin in group.origins:
                if active_proxies == 25:
                    break
                active_proxies += 1
                azure_cdn_proxies = [
                    x for x in origin.proxies
                    if x.provider == "azure_cdn" and x.deprecated is None and x.destroyed is None
                ]
                if not azure_cdn_proxies:
                    proxy = Proxy()
                    proxy.origin_id = origin.id
                    proxy.provider = "azure_cdn"
                    proxy.slug = tldextract.extract(origin.domain_name).domain[:5] + ''.join(
                        random.choices(string.ascii_lowercase, k=random.randint(10, 15)))
                    proxy.url = f"https://{proxy.slug}.azureedge.net"
                    proxy.added = datetime.datetime.utcnow()
                    proxy.updated = datetime.datetime.utcnow()
                    db.session.add(proxy)
            db.session.commit()


def set_urls():
    proxies = Proxy.query.filter(
        Proxy.provider == 'azure_cdn',
        Proxy.destroyed == None
    ).all()
    for proxy in proxies:
        proxy.url = f"https://{proxy.slug}.azureedge.net"
    db.session.commit()


def import_monitor_alerts():
    credential = ClientSecretCredential(
        tenant_id=app.config['AZURE_TENANT_ID'],
        client_id=app.config['AZURE_CLIENT_ID'],
        client_secret=app.config['AZURE_CLIENT_SECRET'])
    client = AlertsManagementClient(
        credential,
        app.config['AZURE_SUBSCRIPTION_ID']
    )
    firing = [x.name[len("bandwidth-out-high-bc-"):]
              for x in client.alerts.get_all()
              if x.name.startswith("bandwidth-out-high-bc-") and x.properties.essentials.monitor_condition == "Fired"]
    for proxy in Proxy.query.filter(
        Proxy.provider == "azure_cdn",
        Proxy.destroyed == None
    ):
        alarm = get_proxy_alarm(proxy.id, "bandwidth-out-high")
        if proxy.origin.group.group_name.lower() not in firing:
            alarm.update_state(AlarmState.OK, "Azure monitor alert not firing")
        else:
            alarm.update_state(AlarmState.CRITICAL, "Azure monitor alert firing")


if __name__ == "__main__":
    with app.app_context():
        auto = ProxyAzureCdnAutomation()
        auto.create_missing_proxies()
        auto.destroy_expired_proxies()
        auto.generate_terraform()
        auto.terraform_init()
        auto.terraform_apply(refresh=False, parallelism=1)  # Rate limits are problem
        set_urls()
        import_monitor_alerts()
