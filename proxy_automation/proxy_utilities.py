"""
Utilities for Proxies
"""
import boto3
import json
import configparser
import datetime
from datetime import tzinfo
from dateutil.tz import tzutc

def cloudfront(**kwargs):
    """
    creates new cloudfront distribution
    :params kwargs: <domain>
    :returns nothing
    """
    configs = get_configs()

    now = str(datetime.datetime.now())
    session = boto3.Session(profile_name=configs['profile'])
    client = session.client('cloudfront', region_name=configs['region'])

    print(f"For domain: {kwargs['domain']}")
    cdn_id = "Custom-" + kwargs['domain']
    response = client.create_distribution(
        DistributionConfig={
            'CallerReference': now,
            'Origins': {
                'Quantity': 1,
                'Items': [ 
                    {
                    'Id': cdn_id,
                    'DomainName': kwargs['domain'],
                    'CustomOriginConfig': {
                        'HTTPPort': 80,
                        'HTTPSPort': 443,
                        'OriginProtocolPolicy': 'match-viewer',
                        'OriginSslProtocols': {
                            'Quantity': 3,
                            'Items': [
                                'TLSv1',
                                'TLSv1.1',
                                'TLSv1.2'
                            ]
                        },
                        'OriginReadTimeout': 30,
                        'OriginKeepaliveTimeout': 5
                        }
                    }
                ] 
            },
            'DefaultCacheBehavior': {
                'TargetOriginId': cdn_id,
                'ForwardedValues': {
                    'QueryString': True,
                    'Cookies': {
                        'Forward': 'none'
                    }
                },
                'TrustedSigners': {
                    'Enabled': False,
                    'Quantity': 0
                },
                'ViewerProtocolPolicy': 'redirect-to-https',
                'MinTTL': 0
            },
            'Comment': 'CDN for ' + kwargs['domain'],
            'PriceClass': 'PriceClass_All',
            'Enabled': True,
            'ViewerCertificate': {
                'CloudFrontDefaultCertificate': True
            }
        }
    )
    print(f"Response: {response}")
    distro_id = response['Distribution']['Id']
    wait = input("Wait for distribution (y/N)?")
    if wait.lower() == 'y':
        print("And now we wait...")
        waiter = client.get_waiter('distribution_deployed')
        waiter.wait(
            Id=distro_id,
            WaiterConfig={
                'Delay': 60,
                'MaxAttempts':30
            }
        )
    return response['Distribution']['DomainName']

def get_configs():
    """
    Gets configs from file
    :params none
    :returns dict with configs
    """
    # Read configs
    config = configparser.ConfigParser()
    
    try:
        config.read('auto.cfg')
    except configparser.Error:
        print('Config File not found or not readable!')
        quit()

    configs = {
        'profile': config.get('AWS', 'profile'),
        'region': config.get('AWS', 'region'),
        'repo': config.get('GITHUB', 'repo'),
        'API_key': config.get('GITHUB', 'API_key'),
        'file': config.get('GITHUB', 'file'),
        'azure_sub_id': config.get('AZURE', 'subscription_id'),
        'azure_tenant_id': config.get('AZURE', 'tenant_id'),
        'azure_app': config.get('AZURE', 'service_principal_app'),
        'azure_key': config.get('AZURE', 'service_principal_key')
    }

    return configs
