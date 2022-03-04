"""
Azure Utilities

Azure add CDN using SDK
Azure Storage retrieval

"""
import os
import re
import datetime
import logging
from system_utilities import get_configs
from simple_AWS.s3_functions import *

logger = logging.getLogger('logger')

from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.cdn import CdnManagementClient
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, __version__
from repo_utilities import get_final_domain

def azure_add(**kwargs):
    configs = get_configs()

    domain = get_final_domain(f"http://{kwargs['domain']}")
    # Tenant ID for your Azure subscription
    TENANT_ID = configs['azure_tenant_id']

    # Your service principal App ID
    CLIENT = configs['azure_app']

    # Your service principal password
    KEY = configs['azure_key']

    logger.debug("Authenticating...")
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

    logger.debug("Adding...")
    endpoint_poller = cdn_client.endpoints.create(my_resource_group,
                                            cdn_name,
                                            endpoint_name,
                                            { 
                                                "location": region,
                                                "origin_host_header": domain,
                                                "origins": [
                                                    {
                                                        "name": cdn_name, 
                                                        "host_name": domain
                                                    }]
                                            })
    endpoint = endpoint_poller.result()

    logger.debug("Done!")
    return endpoint_full_name

def azure_replace(**kwargs):
    return

def retrieve_logs(**kwargs):
    """
    Retrieve logs from storage
    """
    configs = get_configs()

    now = datetime.datetime.now()

    logger.debug("Grabbing files from Azure...")
    # Create a client
    container_name = "insights-logs-azurecdnaccesslog" # it's always called this
    container = ContainerClient.from_connection_string(
        conn_str=configs['azure_storage_conn_string'],
        container_name=container_name)

    date_match = re.compile("y=[0-9]{4}\/m=[0-9]{2}\/d=[0-9]{2}\/h=[0-9]{2}\/m=[0-9]{2}")
    # List blobs
    blob_list = container.list_blobs()
    for blob in blob_list:
    
        try:
            log_date_string = date_match.search(blob.name).group(0)
            log_date = datetime.datetime.strptime(log_date_string, "y=%Y/m=%m/d=%d/h=%H/m=%M")
            #print(f"Date: {log_date} & {log_date_string}")
        except:
            continue

        # right profile?
        #logger.debug(f"Profile: {kwargs['profile_name']} blob.name: {blob.name}")
        if kwargs['profile_name'].upper() not in blob.name:
            #logger.debug('Not right profile')
            continue
        
        # TODO: Find right range of files, copy to S3
        numdays = (now - log_date).days
        if numdays > kwargs['range']:
            logger.debug(f"File {blob.name} too old!")
            continue
        
        file_date = datetime.datetime.strftime(log_date, "%Y-%m-%d-%H-%M")
        s3_filename = "Azure_CDN_log_" + kwargs['profile_name'] + "_" + file_date + ".json"
        local_path = configs['local_tmp'] + "/" + s3_filename
        #logger.debug(f"Local path: {local_path}")

        get_blob = BlobClient.from_connection_string(conn_str=configs['azure_storage_conn_string'], container_name=container_name, blob_name=blob.name)
        with open(local_path, "wb") as tmp_blob:
            blob_data = get_blob.download_blob()
            blob_data.readinto(tmp_blob)

        #upload to S3

        s3simple = S3Simple(region_name=configs['region'], profile=configs['profile'], bucket_name=kwargs['s3_bucket'])
        s3simple.send_file_to_s3(local_file=local_path, s3_file=s3_filename)

        os.remove(local_path)


    return

