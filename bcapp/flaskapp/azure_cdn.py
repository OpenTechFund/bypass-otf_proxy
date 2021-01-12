"""
Azure add CDN using SDK
"""
import logging
from proxy_utilities import get_configs

logger = logging.getLogger('logger')

from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.cdn import CdnManagementClient

def azure_add(**kwargs):
    configs = get_configs()

    # Tenant ID for your Azure subscription
    TENANT_ID = configs['azure_tenant_id']

    # Your service principal App ID
    CLIENT = configs['azure_app']

    # Your service principal password
    KEY = configs['azure_key']

    print("Authenticating...")
    credentials = ServicePrincipalCredentials(
        client_id = CLIENT,
        secret = KEY,
        tenant = TENANT_ID
    )

    endpoint_name = kwargs['domain'][0:6] + '1'
    endpoint_name_confirm = input(f"Azure CDN name/subdomain ({endpoint_name}.azureedge.net)?")
    if endpoint_name_confirm:
        endpoint_name = endpoint_name_confirm

    endpoint_full_name = endpoint_name + '.azureedge.net'
    my_resource_group = 'bypasscensorship'
    region = 'West India'
    tier = 'Standard_Akamai'

    cdn_client = CdnManagementClient(credentials, configs['azure_sub_id'])
    cdn_list = cdn_client.profiles.list()

    print("List of Azure CDNs:")
    count = 0
    names = []
    for profile in cdn_list:
        pf_vars = vars(profile)
        print(f"{count}: Name: {pf_vars['name']}")
        names.append(pf_vars['name'])
        endpoints_list = cdn_client.endpoints.list_by_profile(my_resource_group, pf_vars['name'])
        ep_count = 0
        for endpoint in endpoints_list:
            ep_count += 1
        print(f"Number of endpoints: {ep_count}")

        count += 1

    cdn_choice = input(f"Which CDN to add {endpoint_full_name} to?")
    if not cdn_choice:
        return False
    else:
        cdn_name = names[int(cdn_choice)]

    cdn_confirm = input(f"Add to {cdn_name} (Y/n)?")
    if cdn_confirm.lower() == 'n':
        return False

    print("Adding...")
    endpoint_poller = cdn_client.endpoints.create(my_resource_group,
                                            cdn_name,
                                            endpoint_name,
                                            { 
                                                "location": region,
                                                "origin_host_header": kwargs['domain'],
                                                "origins": [
                                                    {
                                                        "name": cdn_name, 
                                                        "host_name": kwargs['domain']
                                                    }]
                                            })
    endpoint = endpoint_poller.result()

    print("Done!")
    return endpoint_full_name

def azure_replace(**kwargs):
    return