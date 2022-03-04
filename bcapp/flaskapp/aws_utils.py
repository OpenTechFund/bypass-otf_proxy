import boto3
import json
import datetime
import time
import os
import logging
from datetime import tzinfo
from dateutil.tz import tzutc
from system_utilities import get_configs
from dotenv import load_dotenv
import sqlalchemy as db
from simple_AWS.s3_functions import *
from repo_utilities import get_final_domain

logger = logging.getLogger('logger')

def cloudfront_add(**kwargs):
    """
    creates new cloudfront distribution
    :params kwargs
    :kwarg <domain>
    :kwarg [mode]
    :returns url
    """
    configs = get_configs()

    now = str(datetime.datetime.now())
    session = boto3.Session(profile_name=configs['profile'])
    client = session.client('cloudfront', region_name=configs['region'])

    domain = get_final_domain(f"http://{kwargs['domain']}")

    logger.debug(f"For domain: {domain}")
    cdn_id = "Custom-" + domain
    response = client.create_distribution(
        DistributionConfig={
            'CallerReference': now,
            'Origins': {
                'Quantity': 1,
                'Items': [ 
                    {
                    'Id': cdn_id,
                    'DomainName': domain,
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
            'Comment': 'CDN for ' + domain,
            'PriceClass': 'PriceClass_All',
            'Enabled': True,
            'ViewerCertificate': {
                'CloudFrontDefaultCertificate': True
            }
        }
    )
    logger.debug(f"Response: {response}")
    distro_id = response['Distribution']['Id']
    if 'mode' in kwargs and kwargs['mode'] == 'console':
        wait = input("Wait for distribution (y/N)?")
        if wait.lower() == 'y':
            logger.debug("And now we wait...")
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

    if not delete_id: 
        print("Can't find right distribution - check domain name!")
        return

    # Get config
    distro_config = client.get_distribution_config(Id=delete_id)
    logger.debug(f"Configuration: {distro_config}")
    etag = distro_config['ETag']
    disable_config = dict(distro_config['DistributionConfig'])
    disable_config['Enabled'] = False

    # Update config to disable
    response = client.update_distribution(DistributionConfig=disable_config, Id=delete_id, IfMatch=etag)
    d_etag = response['ETag']

    # Wait for it...
    logger.debug("Waiting for distribution to be disabled...")
    waiter = client.get_waiter('distribution_deployed')
    waiter.wait(Id=delete_id)

    # Delete it.
    response = client.delete_distribution(Id=delete_id, IfMatch=d_etag)

    # Create a new distribution
    new_mirror = cloudfront_add(domain=domain)
    
    return new_mirror

def add_s3_storage(domain, s3):
    """
    Add Storage Bucket
    """
    configs = get_configs()
    
    load_dotenv()
    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    domains = db.Table('domains', metadata, autoload=True, autoload_with=engine)

    query = db.select([domains]).where(domains.c.domain == domain)
    result = connection.execute(query)
    row = result.fetchone()

    logger.debug(f"Domain: {row} S3 storage {type(row.s3_storage_bucket)}")
    if row.s3_storage_bucket:
        return 'bucket_exists'
    else:
        s3simple = S3Simple(region_name=configs['region'], profile=configs['profile'], bucket_name=s3)
        new_bucket = s3simple.s3_new_bucket()

    row.s3_storage_bucket = s3
    session.commit()
    
    return 'bucket_created'

def cloudfront_add_logging(domain):
    """
    Add logging for a cloudfront distribution
    """
    load_dotenv()
    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    domains = db.Table('domains', metadata, autoload=True, autoload_with=engine)

    query = db.select([domains]).where(domains.c.domain == domain)
    result = connection.execute(query)
    row = result.fetchone()

    logger.debug(f"Domain: {row} S3 storage {row.s3_storage_bucket}")
    
    if not row.s3_storage_bucket:
        logger.debug("No S3 Storage set up!")
        return False

    # Find distribution based on domain
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

    edit_id = False
    for distribution in distributions:
        if domain in distribution['Origins']['Items'][0]['DomainName']: # it's what we want to edit
            edit_id = distribution['Id']
            
    if not edit_id: 
        logger.debug("Can't find right distribution - check domain name!")
        return False

    # Get config
    distro_config = client.get_distribution_config(Id=edit_id)
    logger.debug(f"Configuration: {distro_config}")
    etag = distro_config['ETag']
    new_config = dict(distro_config['DistributionConfig'])
    new_config['Logging'] =  {
            'Enabled': True,
            'IncludeCookies': False,
            'Bucket': row.s3_storage_bucket,
            'Prefix': ''
        }
    
    # Update config to add logging
    response = client.update_distribution(DistributionConfig=new_config, Id=edit_id, IfMatch=etag)
    d_etag = response['ETag']
    logger.debug(f"Response: {response}")

    # Wait for it...
    logger.debug("Waiting for distribution to be reconfigured...")
    waiter = client.get_waiter('distribution_deployed')
    waiter.wait(Id=edit_id)

    logger.debug("Distribution updated!")

    return True

