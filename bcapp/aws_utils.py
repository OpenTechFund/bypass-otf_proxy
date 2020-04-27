import boto3
import json
import datetime
import time
from datetime import tzinfo
from dateutil.tz import tzutc
from proxy_utilities import get_configs

def cloudfront_add(**kwargs):
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

def cloudfront_replace(domain, replace):
    """
    Replaces cloudfront distribution
    :param <domain>
    :param <replace>
    """
    # Find distribution based on replace domain
    configs = get_configs()
    session = boto3.Session(profile_name=configs['profile'])
    client = session.client('cloudfront', region_name=configs['region'])

    distributions = []
    truncated = True
    marker = ''
    while truncated:
        distribution_list = client.list_distributions(Marker=marker)
        distributions.extend(distribution_list['DistributionList']['Items'])
        if not distribution_list['DistributionList']['IsTruncated']:
            truncated = False
        else:
            marker = distribution_list['DistributionList']['NextMarker']

    for distribution in distributions:
        if distribution['DomainName'] == replace: #it's the one to be replaced
            delete_id = distribution['Id']

    # Get config
    distro_config = client.get_distribution_config(Id=delete_id)
    print(f"Configuration: {distro_config}")
    etag = distro_config['ETag']
    disable_config = dict(distro_config['DistributionConfig'])
    disable_config['Enabled'] = False

    # Update config to disable
    response = client.update_distribution(DistributionConfig=disable_config, Id=delete_id, IfMatch=etag)
    d_etag = response['ETag']

    # Wait for it...
    print("Waiting for distribution to be disabled...")
    waiter = client.get_waiter('distribution_deployed')
    waiter.wait(Id=delete_id)

    # Delete it.
    response = client.delete_distribution(Id=delete_id, IfMatch=d_etag)

    # Create a new distribution
    new_mirror = cloudfront_add(domain=domain)
    
    return new_mirror
