"""
This is meant to be run periodically to renew all ECS mirrors
"""
import boto3
import json
import re
import time
from datetime import tzinfo
from dateutil.tz import tzutc
from aws_utils import get_ip
from proxy_utilities import get_configs
from repo_utilities import domain_list, add

def mirror_renew():
    configs = get_configs()

    dom_list = domain_list()
    ip_list = {}
    for domain in dom_list['sites']:
        for mirror in domain['available_mirrors']:
            ip_addr = re.search('[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', mirror)
            if ip_addr: # there's an IP there
                ip_list[domain['main_domain']] = mirror

    session = boto3.Session(profile_name=configs['profile'])
    client = session.client('ecs', region_name=configs['region'])

    clusters = client.list_clusters()
    cluster_list = clusters['clusterArns']

    for cluster_arn in cluster_list:
        task_arns = client.list_tasks(
            cluster=cluster_arn,
            desiredStatus='RUNNING'
        )['taskArns']
        if task_arns:
            ec2_client = session.client('ec2', region_name=configs['region'])
            task_arns = client.list_tasks(cluster=cluster_arn)['taskArns']
            task_details = client.describe_tasks(cluster=cluster_arn, tasks=task_arns)
            for task in task_details['tasks']:
                net_details = task['attachments'][0]['details']
                for detail in net_details:
                    if detail['name'] == 'networkInterfaceId':
                        nets = ec2_client.describe_network_interfaces(NetworkInterfaceIds=[detail['value']])
                        net_info = nets['NetworkInterfaces'][0]['Association']
                        ip_address = net_info['PublicIp']
                        for domain in ip_list:
                            if ip_address in ip_list[domain]:
                                if '/' in ip_list[domain]:
                                    old_ip, mirror_specifics = ip_list[domain].split('/', 1)
                                    mirror_specifics = '/' + mirror_specifics
                                else:
                                    mirror_specifics = ''
                                task_definition_ARN = task['taskDefinitionArn']
                                group = task['group']
                                prefix, service = group.split(':')
                                task_arn = task['taskArn']

                                # Stop task
                                response = client.stop_task(
                                    cluster=cluster_arn,
                                    task=task_arn
                                )
                                # Wait
                                waiter = client.get_waiter('services_stable')
                                waiter.wait(cluster=cluster_arn, services=[service])  
                                # and wait some more 5 minutes for mirror to populate
                                time.sleep(300)

                                ip = get_ip(cluster_arn, task_arns, task_definition_ARN)
                                new_mirror = ip + mirror_specifics
                                print(f"Replacing {domain} mirror with New IP: {ip} - final new mirror: {new_mirror}")

                                domain_listing = add(domain=domain,
                                        mirror=[new_mirror],
                                        pre=True,
                                        replace=ip_list[domain],
                                        quiet=True)

if __name__ == '__main__':
    mirror_renew()