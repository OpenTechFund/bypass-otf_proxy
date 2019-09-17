import boto3
import json
import datetime
from datetime import tzinfo
from dateutil.tz import tzutc
from proxy_utilities import get_configs

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

def ecs(**kwargs):
    """
    Creates ECS task definition, and service using that definition
    :param kwargs: <domain>
    :returns
    """
    configs = get_configs()
    session = boto3.Session(profile_name=configs['profile'])
    client = session.client('ecs', region_name=configs['region'])

    old_new = input("Use an existing task definition, or create a new one (e/N)?")
    if old_new.lower() != 'e':
        # First step, create (register) task definition
        name = input("Name of task definition?")
        url = input(f"Specific URL to mirror of {kwargs['domain']}?")
        replacement_urls = input("List of replacement URLs (comma-delimted, no spaces)?")
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
    print(f"Response: {response}")
    

    # Third step, create the service with task definition
    # Fourth step, verify?
    return