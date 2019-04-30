"""
Utilities for Proxies
"""
import boto3
import json
import configparser
import datetime

def cdn(**kwargs):
    """
    creates new distribution
    :params kwargs: <domain>
    :returns nothing
    """
    configs = get_configs()

    now = str(datetime.datetime.now())
    session = boto3.Session(profile_name=configs['profile'])
    client = session.client('cloudfront', region_name=configs['region'])

    cdn_id = kwargs['domain'] + '1'
    response = client.create_distribution(
        DistributionConfig={
            'CallerReference': now,
            'Origins': {
                'Quantity': 1,
                'Items': [ 
                    {
                    'Id': cdn_id,
                    'DomainName': kwargs['domain']
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
        'repo': config.get('GITHUB', 'repo')
    }

    return configs

def create_log_group(log_group):
    """
    Creates Log Group in Cloudwatch
    :param <shortcut> name of log group
    """
    configs = get_configs()
    print(f"Configs: {configs}")
    session = boto3.Session(profile_name=configs['profile'])
    client = session.client('logs', region_name=configs['region'])
    response = client.create_log_group(
        logGroupName=log_group,
    )

    return response

def delete_log_group(shortcut):
    """
    Deletes Log Group in Cloudwatch
    :param <shortcut> - name of log group
    """
    configs = get_configs()
    session = boto3.Session(profile_name=configs['profile'])
    client = session.client('logs', region_name=configs['region'])
    response = client.delete_log_group(
        logGroupName=shortcut
    )

def create_task(**kwargs):
    """
    Creates Task in ECS
    :param kwargs: <shortcut> - name of task
    :param kwargs: <log_group> - log group name
    :param kwargs: <domain> - domain being proxied
    """

    configs = get_configs()
    # Read containers file
    with open ('ecs_containers.json') as cfile:
        containers = json.load(cfile)

    bypass_hostfull = kwargs['shortcut'] + '.' + configs['bypass_host']

    for container in containers:
        container["logConfiguration"]["options"]["awslogs-group"] = kwargs['log_group']
        if container["name"] == 'nginx':
            container["image"] = configs['proxy_image']
            for env in container["environment"]:
                if env["name"] == "TARGET_SERVER":
                    env["value"] = kwargs['domain']
        elif container["name"] == 'cloudflared':
            container["image"] = configs['cloudflared_image']
            for env in container["environment"]:
                if env["name"] == "CF_TUNNEL_HOSTNAME":
                    env["value"] == bypass_hostfull

    print(f"Container Definitions: {containers}")

    session = boto3.Session(profile_name=configs['profile'])
    client = session.client('ecs', region_name=configs['region'])
    response = client.register_task_definition(
        family=kwargs['shortcut'],
        taskRoleArn=configs['ecs_role_arn'],
        executionRoleArn=configs['ecs_role_arn'],
        networkMode='awsvpc',
        containerDefinitions=containers,
        requiresCompatibilities=[
            'EC2',
            'FARGATE'
        ],
        cpu=configs['ecs_cpu'],
        memory=configs['ecs_memory']
    )

    print(f"Response: {response}")

    return