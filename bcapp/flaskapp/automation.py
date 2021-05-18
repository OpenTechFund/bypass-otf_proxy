"""
Automation of Creation of CDN and...

version 0.4
"""
import sys
import configparser
import logging
from aws_utils import cloudfront_add, cloudfront_replace, cloudfront_add_logging, add_s3_storage
from repo_utilities import add, check, domain_list, remove_domain, remove_mirror, convert_domain, convert_all
from report_utilities import domain_reporting, send_report, generate_admin_report
from log_reporting_utilities import domain_log_reports, domain_log_list
from mirror_tests import mirror_detail
from fastly_add import fastly_add, fastly_replace
from azure_utilities import azure_add, azure_replace
from system_utilities import get_configs
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
@click.option('--log', type=click.Choice(['enable', 'disable']), help="Enable or Disable Logging")
@click.option('--s3', type=str, help="Add this s3 log storage bucket")
@click.option('--remove', type=str, help="Mirror or onion to remove")
@click.option('--domain_list', is_flag=True, default=False, help="List all domains and mirrors/onions")
@click.option('--mirror_list', is_flag=True, help="List mirrors for domain")
@click.option('--mirror_type', type=click.Choice(['cloudfront', 'azure', 'fastly', 'onion', 'mirror', 'ipfs']), help="Type of mirror")
@click.option('--nogithub', is_flag=True, default=False, help="Do not add to github")
@click.option('--report', is_flag=True, default=False, help="Get report from api database")
@click.option('--generate_report', is_flag=True, default=False, help="Generate report and possibly send email to admins, etc.")
@click.option('--mode', type=click.Choice(['daemon', 'web', 'console']), default='console', help="Mode: daemon, web, console")

def automation(testing, domain, proxy, existing, delete, domain_list, mirror_list, log,
    mirror_type, replace, nogithub, remove, report, mode, num, generate_report, s3):
    if domain:
        if delete:
            delete_domain(domain, nogithub)
        elif replace:
            convert_domain(domain, 'n')
            replace_mirror(domain=domain, existing=existing, replace=replace, nogithub=nogithub, mirror_type=mirror_type)
        elif remove:
            convert_domain(domain, 'n')
            remove_mirror(domain=domain, remove=remove, nogithub=nogithub)
        elif log:
            add_logging(domain=domain, mirror_type=mirror_type, mode=mode)
        elif s3:
            s3_storage_add = add_s3_storage(domain=domain, s3=s3)
            if mode == 'console':
                print (f"Result: {s3_storage_add}")
        elif mirror_type or existing:
            convert_domain(domain, 'n')
            new_add(domain=domain, mirror_type=mirror_type, nogithub=nogithub, existing=existing)
        elif report:
            domain_reporting(domain=domain, mode=mode)
        else:
            domain_data = mirror_detail(domain=domain, proxy=proxy, mode=mode, testing=False)
            if mode == 'console':
                if not domain_data:
                    print("No data returned!")
            return

    elif testing:
        if mode == 'console':
            test = input("Test all (Y/n)?")
        else:
            test = 'y'
        if test.lower() != 'n':
            domain_testing(testing, proxy, mode)
        if mode == 'console':
            convert = input("Convert all (y/N)?")
            if convert.lower() == 'y':
                convert_all()
    elif generate_report:
        generate_admin_report(mode)
            
    elif domain_list: #assuming console mode
        dlist = domain_list()
        print(f""" List of all domains, mirrors and onions
        ___________________________________________________
        {dlist}
        ___________________________________________________
        """)
    else:
        click.echo("Invalid parameters! try --help")
    return

def add_logging(domain, mirror_type, mode):
    """
    Add logging to proxy
    """
    if not mirror_type:
        if mode == 'console':
            print("You must include mirror type!")
        return False
    if mirror_type == 'cloudfront':
        log_add = cloudfront_add_logging(domain)
        if not log_add and mode == 'console':
            print("Log couldn't be added!")
    else:
        if mode == 'console':
            print("That mirror type is not supported!")
        return False

    return log_add

def domain_testing(testing, proxy, mode):
    """
    Tests domains, mirrors and onions in repo
    """
    mirror_list = domain_list()
    for domain in mirror_list['sites']:
        domain_data = mirror_detail(domain=domain['main_domain'], proxy=proxy, mode=mode, test=True)
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
    current_alternatives = domain_data['available_alternatives']
    if not exists:
        print("Domain doesn't exist!")
        return

    if 'mirror_type' not in kwargs:
        print("Need mirror type here!!")
        return

    if kwargs['mirror_type'] == 'onion':
        proto = 'tor'
        mtype = 'eotk'
    elif kwargs['mirror_type'] == 'mirror':
        proto = 'http'
        mtype = 'mirror'
    else:
        proto = 'https'
        mtype = 'proxy'

    if 'existing' in kwargs and kwargs['existing']: # replacing with existing...
        if kwargs['nogithub']:
            print("You wanted to replace with existing but didn't want it added to github! Bye!")
            return
        domain_listing = add(domain=kwargs['domain'], 
                             mirror=kwargs['existing'], 
                             pre=exists,
                             replace=kwargs['replace'],
                             proto=proto,
                             mtype=mtype
                            )
    else: # need to create a new mirror from the old automatically
        if kwargs['mirror_type'] == 'cloudfront':
            mirror = cloudfront_replace(kwargs['domain'], kwargs['replace'])
            domain_listing = add(domain=kwargs['domain'],
                                 mirror=mirror,
                                 pre=exists,
                                 replace=kwargs['replace'],
                                 proto=proto,
                                 mtype=mtype)
        else:
            print("Sorry, only cloudfront is automated!!")
    return

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
    if 'exists' not in domain_data:
        exists = False
    else:
        exists = domain_data['exists']
    if 'current_alternatives' in domain_data:
        current_alternatives = domain_data['available_alternatives']
    else:
        current_alternatives = []
    print(f"Preexisting: {exists}, current alternatives {current_alternatives}")
    print(f"Adding entry to {kwargs['mirror_type']} ...")
    if kwargs['mirror_type'] == 'cloudfront':
        proto = 'https'
        mtype = 'proxy'
        if kwargs['existing']:
            mirror = kwargs['existing']
        else:
            mirror = cloudfront_add(domain=kwargs['domain'])
    elif kwargs['mirror_type'] == 'azure':
        proto = 'https'
        mtype = 'proxy'
        if kwargs['existing']:
            mirror = kwargs['existing']
        else:
            mirror = azure_add(domain=kwargs['domain'])
    elif kwargs['mirror_type'] == 'fastly':
        proto = 'https'
        mtype = 'proxy'
        if kwargs['existing']:
            mirror = kwargs['existing']
        else:
            mirror = fastly_add(domain=kwargs['domain'])
    elif kwargs['mirror_type'] == 'onion':
        proto = 'tor'
        mtype = 'eotk'
        if 'existing' in kwargs:
            mirror = kwargs['existing']
        else:
            print("Need to include existing url!")
    elif kwargs['mirror_type'] == 'ipfs':
        proto = 'https'
        mtype = 'ipfs'
        if 'existing' not in kwargs:
            mirror = ipfs_add(domain=kwargs['domain'])
        else:
            mirror = kwargs['existing']
    elif kwargs['mirror_type'] == 'mirror':
        proto = 'http'
        mtype = 'mirror'
        if 'existing' not in kwargs:
            print("You didn't include URL - mirror type needs that!")
            return
        mirror = kwargs['existing']
    else:
        print("Need to define type of mirror. Use --mirror_type=cloudfront/azure/fastly/onion/mirror/ipfs")
        return

    if not mirror:
        print(f"Sorry, mirror not created for {kwargs['domain']}!")
        return

    replace = False
   
    if kwargs['nogithub']:
        print(f"You added this mirror: {mirror}. But no changes were made to github")
        return
    else:
        domain_listing = add(domain=kwargs['domain'], mirror=mirror, pre=exists, proto=proto, mtype=mtype)
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
