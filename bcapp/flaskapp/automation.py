"""
Automation of Creation of CDN and...

version 0.4
"""
import sys
import configparser
import logging
from aws_utils import cloudfront_add, cloudfront_replace
from repo_utilities import add, check, domain_list, remove_domain, remove_mirror
from report_utilities import domain_reporting, send_report
from log_reporting_utilities import domain_log_reports, domain_log_list
from mirror_tests import mirror_detail
from fastly_add import fastly_add, fastly_replace
from azure_cdn import azure_add, azure_replace
from proxy_utilities import get_configs
from ipfs_utils import ipfs_add
import click

@click.command()
@click.option('--testing', is_flag=True, default=False, help="Domain testing of all available mirrors and onions")
@click.option('--domain', help="Domain to act on", type=str)
@click.option('--num', help="Number of Raw Log files to list", type=int, default=5)
@click.option('--proxy', type=str, help="Proxy server to use for testing/domain detail.")
@click.option('--existing', type=str, help="Mirror exists already, just add to github.")
@click.option('--replace', type=str, help="Mirror/onion to replace.")
@click.option('--delete', is_flag=True, default=False, help="Delete a domain from list")
@click.option('--remove', type=str, help="Mirror or onion to remove")
@click.option('--domain_list', is_flag=True, default=False, help="List all domains and mirrors/onions")
@click.option('--mirror_list', is_flag=True, help="List mirrors for domain")
@click.option('--mirror_type', type=click.Choice(['cloudfront', 'azure', 'fastly', 'onion', 'ipfs']), help="Type of mirror")
@click.option('--nogithub', is_flag=True, default=False, help="Do not add to github")
@click.option('--report', is_flag=True, default=False, help="Get report from api database")
@click.option('--mode', type=click.Choice(['daemon', 'web', 'console']), default='console', help="Mode: daemon, web, console")

def automation(testing, domain, proxy, existing, delete, domain_list, mirror_list,
    mirror_type, replace, nogithub, remove, report, mode, num):
    if domain:
        if delete:
            delete_domain(domain, nogithub)
        elif replace:
            replace_mirror(domain=domain, existing=existing, replace=replace, nogithub=nogithub, mirror_type=mirror_type)
        elif mirror_type or existing:
            new_add(domain=domain, mirror_type=mirror_type, nogithub=nogithub, existing=existing)
        elif remove:
            remove_mirror(domain=domain, remove=remove, nogithub=nogithub)
        elif report:
            domain_reporting(domain=domain, mode=mode)
        else:
            domain_data = mirror_detail(domain=domain, proxy=proxy, mode=mode)
            if not domain_data:
                return
            reports_list = domain_log_list(domain, num)
            report = domain_log_reports(domain, 'latest')
            reporting = send_report(domain_data, mode)
            if mode =='console':
                print(f"Latest {num} log files:")
                for rpt in reports_list:
                    date = rpt['date'].strftime('%m/%d/%Y:%H:%M:%S.%f')
                    print(f"{date} : {rpt['file_name']}")
                print(f"Reported? {reporting}")
                if not report:
                    print("No log reports stored!")
                else:
                    print(f"Latest Log Report: \n {report}")

    else:
        if testing:
            domain_testing(testing, proxy, mode)
    
        if domain_list:
            dlist = domain_list()
            print(f""" List of all domains, mirrors and onions
            ___________________________________________________
            {dlist}
            ___________________________________________________
            """)
    return

def domain_testing(testing, proxy, mode):
    """
    Tests domains, mirrors and onions in repo
    """
    mirror_list = domain_list()
    for domain in mirror_list['sites']:
        domain_data = mirror_detail(domain=domain['main_domain'], proxy=proxy, mode=mode)
        reporting = send_report(domain_data, mode)
        if mode =='console':
            print(f"Reported? {reporting}")
    return


def delete_domain(domain, nogithub):
    """
    Delete domain
    :arg domain
    :arg nogithub
    :returns nothing
    """
    print(f"Deleting {domain}...")
    domain_data = check(domain)
    exists = domain_data['exists'] 
    current_mirrors = domain_data['available_mirrors']
    current_onions = domain_data['available_onions'] 
    current_ipfs_nodes = domain_data['available_ipfs_nodes']
    print(f"Preexisting: {exists}, current Mirrors: {current_mirrors}, current onions: {current_onions}, current IPFS nodes: {current_ipfs_nodes}")
    if not exists:
        print("Domain doesn't exist!")
        return
    elif nogithub:
        print("You said you wanted to delete a domain, but you also said no to github. Bye!")
        return
    else:
        removed = remove_domain(domain)

    if removed:
        print(f"{domain} removed from repo.")
    else:
        print(f"Something went wrong. {domain} not removed from repo.")

    return

def replace_mirror(**kwargs):
    """
    Replace Mirror or Onion
    :kwarg <domain>
    :kwarg <replace>
    :kwarg [existing]
    :kwarg [mirror_type]
    :kwarg [nogithub]
    :returns nothing
    """
    print(f"Replacing mirror for: {kwargs['domain']}...")
    domain_data = check(kwargs['domain'])
    exists = domain_data['exists'] 
    current_mirrors = domain_data['available_mirrors']
    current_onions = domain_data['available_onions'] 
    current_ipfs_nodes = domain_data['available_ipfs_nodes']
    if not exists:
        print("Domain doesn't exist!")
        return
    else:
        if 'mirror_type' not in kwargs:
            kwargs['mirror_type'] = False
        if 'existing' in kwargs and kwargs['existing']: # replacing with existing...
            if kwargs['nogithub']:
                print("You wanted to replace with existing but didn't want it added to github! Bye!")
                return
            domain_listing = add(domain=kwargs['domain'], 
                                 mirror=[kwargs['existing']], 
                                 pre=exists,
                                 replace=kwargs['replace']
                                )
        else: # need to create a new mirror from the old
            if 'mirror_type' not in kwargs:
                print("Need to define --mirror_type=fastly/azure/cloudfront/onion/ipfs")
                return
            if kwargs['mirror_type'] == 'fastly':
                mirror = fastly_replace(kwargs['domain'], kwargs['replace'])
            elif kwargs['mirror_type'] == 'cloudfront':
                mirror = cloudfront_replace(kwargs['domain'], kwargs['replace'])
            elif kwargs['mirror_type'] == 'azure':
                mirror = azure_replace(kwargs['domain'], kwargs['replace'])
            elif kwargs['mirror_type'] == 'onion':
                mirror = onion_add(kwargs['domain'], kwargs['replace'])
            elif kwargs['mirror_type'] == 'ipfs':
                mirror = ipfs_add(kwargs['domain'], kwargs['replace'])
            else:
                print("Incorrect mirror definition! Must be one of: fastly/azure/cloudfront/onion/ipfs")
                return

            if kwargs['nogithub']:
                print(f"New mirror: {mirror}. Not added to Github!")
                return
            else:
                domain_listing = add(domain=kwargs['domain'],
                                    mirror=[mirror],
                                    pre=exists,
                                    replace=kwargs['replace'])
    return

def onion_add(**kwargs):
    """
    Not automated
    :kwarg <domain>
    :returns onion from user input
    """
    mirror = input(f"Name of onion for {kwargs['domain']}?")
    return mirror

def new_add(**kwargs):
    """
    Add new domain, mirror, onion or ipfs
    :kwarg <domain>
    :kwarg <mirror_type>
    :kwarg [existing]
    :kwarg [nogithub]
    :returns nothing
    """
    mirror = ""
    domain_data = check(kwargs['domain'])
    exists = domain_data['exists'] 
    current_mirrors = domain_data['available_mirrors']
    current_onions = domain_data['available_onions'] 
    current_ipfs_nodes = domain_data['available_ipfs_nodes']
    print(f"Preexisting: {exists}, current Mirrors: {current_mirrors}, current onions: {current_onions}, current IPFS nodes: {current_ipfs_nodes}")
    if not kwargs['existing']: #New mirror
        print(f"Adding distribution to {kwargs['mirror_type']} ...")
        if kwargs['mirror_type'] == 'cloudfront':
            mirror = cloudfront_add(domain=kwargs['domain'])
        elif kwargs['mirror_type'] == 'azure':
            mirror = azure_add(domain=kwargs['domain'])
        elif kwargs['mirror_type'] == 'fastly':
            mirror = fastly_add(domain=kwargs['domain'])
        elif kwargs['mirror_type'] == 'onion':
            mirror = onion_add(domain=kwargs['domain'])
        if kwargs['mirror_type'] == 'ipfs':
            mirror = ipfs_add(domain=kwargs['domain'])
        else:
            print("Need to define type of mirror. Use --mirror_type=cloudfront/azure/fastly/onion/ipfs")
            return
        if not mirror:
            print(f"Sorry, mirror not created for {kwargs['domain']}!")
            return
        elif kwargs['nogithub']:
            print(f"Mirror {mirror} added, but not added to Github as per your instructions!")
            return
        replace = False
    else: #adding existing mirror/onion/ipfs
        if kwargs['nogithub']:
            print(f"You asked to add or replace an existing mirror but then didn't want it added to github! Bye!")
            return
        mirror = kwargs['existing']

    if kwargs['nogithub']:
        print(f"You added this mirror: {mirror}. But no changes were made to github")
        return
    else:
        domain_listing = add(domain=kwargs['domain'], mirror=[mirror], pre=exists)
        print(f"New Domain listing: {domain_listing}")
        return

if __name__ == '__main__':
    configs = get_configs()
    log = configs['log_level']
    logger = logging.getLogger('logger')  # instantiate clogger
    logger.setLevel(logging.DEBUG)  # pass DEBUG and higher values to handler

    ch = logging.StreamHandler()  # use StreamHandler, which prints to stdout
    ch.setLevel(configs['log_level'])  # ch handler uses the configura

    # create formatter
    # display the function name and logging level in columnar format if
    # logging mode is 'DEBUG'
    formatter = logging.Formatter('[%(funcName)24s] [%(levelname)8s] %(message)s')

    # add formatter to ch
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    automation()
