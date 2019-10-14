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

def ecs_add(**kwargs):
    """
    Creates ECS task definition, and service using that definition
    :param kwargs: <domain>
    :param kwargs: 
    :returns
    """
    configs = get_configs()
    session = boto3.Session(profile_name=configs['profile'])
    client = session.client('ecs', region_name=configs['region'])

    old_new = input("Use an existing task definition, or create a new one (e/N)?")
    if old_new.lower() != 'e':
        # First step, create (register) task definition
        name = input("Name of task definition?")
        url = input(f"Specific URL to mirror (e.g. https://www.{kwargs['domain']}/something)?")
        replacement_urls = input("List of replacement URLs (comma-delimted, no spaces, return for none)?")
        task_memory = input("Task Memory (512MiB)?")
        if not task_memory:
            task_memory = '512'
        cpu = input("CPU (256)?")
        if not cpu:
            cpu = '256'
        response = client.register_task_definition(
            family=name,
            executionRoleArn=configs['roleArn'],
            networkMode='awsvpc',
            containerDefinitions=[
                {
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                        "awslogs-group": configs['ecs_log_group'],
                        "awslogs-region": configs['region'],
                        "awslogs-stream-prefix": "ecs"
                        }
                    },
                    "portMappings": [
                        {
                        "hostPort": 80,
                        "protocol": "tcp",
                        "containerPort": 80
                        }
                    ],
                    "cpu": 0,
                    "environment": [
                        {
                        "name": "REPLACE_URLS",
                        "value": replacement_urls
                        },
                        {
                        "name": "URL",
                        "value": url
                        }
                    ],
                    "mountPoints": [],
                    "volumesFrom": [],
                    "image": configs['mirror_docker_image'],
                    "essential": True,
                    "name": "mirror_container"
                    }
            ],
            placementConstraints=[],
            requiresCompatibilities=['FARGATE'],
            cpu=cpu,
            memory=task_memory
        )
        task_definition_ARN = response['taskDefinition']['taskDefinitionArn']
        print(f"Task definition ARN: {task_definition_ARN}")
    else:
        tasks_list = client.list_task_definitions()['taskDefinitionArns']
        tl = 0
        for task in tasks_list:
            print(f"{tl}: {task}")
            tl += 1
    
        task_choice = input("Which task to make a service?")
        if not task_choice:
            return
        task_definition_ARN = tasks_list[int(task_choice)]
        print(f"ARN: {task_definition_ARN}")
     
    # Second step, list clusters so we can choose where to start the service
    clusters = client.list_clusters()
    cluster_list = clusters['clusterArns']
    cl = 0
    for cluster in cluster_list:
        print(f"{cl}: {cluster}")
        cl += 1
    
    cluster_choice = input("Which cluster to add service to?")
    if not cluster_choice:
        return
    cluster_arn = cluster_list[int(cluster_choice)]
    print(cluster_arn)

    if 'name' not in locals():
        name = input("Service Name?")
    response = client.create_service(
        cluster=cluster_arn,
        serviceName=name,
        taskDefinition=task_definition_ARN,
        loadBalancers=[],
        serviceRegistries=[],
        desiredCount=1,
        launchType='FARGATE',
        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets': [configs['subnet']],
                'securityGroups': [configs['security_group']],
                'assignPublicIp': 'ENABLED'
            }
        }
    )
    service = response['service']['serviceArn']
    # Wait
    print("Waiting for services to be stable...")
    waiter = client.get_waiter('services_stable')
    waiter.wait(cluster=cluster_arn, services=[service])  
    # and wait some more 5 minutes for mirror to populate
    print("Waiting for mirror to populate...")
    time.sleep(300)          

    # Super convoluted way to get DNS name for mirror
    ec2_client = session.client('ec2', region_name=configs['region'])
    task_arns = client.list_tasks(cluster=cluster_arn)['taskArns']
    task_details = client.describe_tasks(cluster=cluster_arn, tasks=task_arns)
    for task in task_details['tasks']:
        print(f"Task: {task['taskDefinitionArn']}")
        if task['taskDefinitionArn'] == task_definition_ARN:
            net_details = task['attachments'][0]['details']                                                                                                                                                    
            for detail in net_details:
                if detail['name'] == 'networkInterfaceId':
                    nets = ec2_client.describe_network_interfaces(NetworkInterfaceIds=[detail['value']])
                    print(nets['NetworkInterfaces'][0]['Association'])
                    mirror = nets['NetworkInterfaces'][0]['Association']['PublicIp']
                    print(f"Mirror: {mirror}")

    return mirror

def ecs_replace(domain, replace):
    """
    Replacing IP address by restarting ECS service
    """
    configs = get_configs()
    session = boto3.Session(profile_name=configs['profile'])
    client = session.client('ecs', region_name=configs['region'])

    # Which cluster?
    clusters = client.list_clusters()
    cluster_list = clusters['clusterArns']
    cl = 0
    for cluster in cluster_list:
        print(f"{cl}: {cluster}")
        cl += 1
    
    cluster_choice = input("Which cluster is this service in?")
    if not cluster_choice:
        return
    cluster_arn = cluster_list[int(cluster_choice)]
    print(cluster_arn)

    # Which Task?
    task_arns = client.list_tasks(
        cluster=cluster_arn,
        desiredStatus='RUNNING'
    )['taskArns']
    task_details = client.describe_tasks(cluster=cluster_arn, tasks=task_arns)
    tl = 0
    for task in task_details['tasks']:
        print(f"{tl}: {task['taskDefinitionArn']}")
        tl += 1

    task_choice = input("Which task to change?")
    if not task_choice:
        return
    else:
        task_ARN = task_arns[int(task_choice)]
        task_definition_ARN = task_details['tasks'][int(task_choice)]['taskDefinitionArn']
        group = task_details['tasks'][int(task_choice)]['group']
        prefix, service = group.split(':')
    
    # Stop task
    response = client.stop_task(
        cluster=cluster_arn,
        task=task_ARN
    )

    # Wait
    print("Waiting for services to be stable...")
    waiter = client.get_waiter('services_stable')
    waiter.wait(cluster=cluster_arn, services=[service])  
    # and wait some more 5 minutes for mirror to populate
    print("Waiting for mirror to populate...")
    time.sleep(300)

    # Get IP

    ec2_client = session.client('ec2', region_name=configs['region'])
    task_arns = client.list_tasks(cluster=cluster_arn)['taskArns']
    task_details = client.describe_tasks(cluster=cluster_arn, tasks=task_arns)
    for task in task_details['tasks']:
        print(f"Task: {task['taskDefinitionArn']}")
        if task['taskDefinitionArn'] == task_definition_ARN:
            net_details = task['attachments'][0]['details']                                                                                                                                                    
            for detail in net_details:
                if detail['name'] == 'networkInterfaceId':
                    nets = ec2_client.describe_network_interfaces(NetworkInterfaceIds=[detail['value']])
                    print(nets['NetworkInterfaces'][0]['Association'])
                    mirror = nets['NetworkInterfaces'][0]['Association']['PublicIp']
                    print(f"Mirror: {mirror}")

    return mirror