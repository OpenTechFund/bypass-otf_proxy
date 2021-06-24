"""
Automation of Creation of CDN and...

version 0.4
"""
import sys
import configparser
import logging
from aws_utils import cloudfront_add, cloudfront_replace, cloudfront_add_logging, add_s3_storage
from repo_utilities import add, check, domain_list, missing_mirrors, remove_domain, remove_mirror, strip_www, delete_deprecated
from report_utilities import domain_reporting, send_report, generate_admin_report, get_ooni_data
from log_reporting_utilities import domain_log_reports, domain_log_list
from mirror_tests import mirror_detail
from fastly_add import fastly_add, fastly_replace
from azure_utilities import azure_add, azure_replace
from system_utilities import get_configs
from ipfs_utils import ipfs_add
import click

type_choice = ['cloudfront', 'azure', 'fastly', 'onion', 'mirror', 'ipfs']

@click.command()
@click.option('--testing', is_flag=True, default=False, help="Domain testing of all available mirrors and onions")
@click.option('--domain', help="Domain to act on", type=str)
@click.option('--test', is_flag=True, default=False, help="Test when listing domain")
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
@click.option('--mirror_type', type=click.Choice(type_choice), help="Type of mirror")
@click.option('--nogithub', is_flag=True, default=False, help="Do not add to github")
@click.option('--report', is_flag=True, default=False, help="Get report from api database")
@click.option('--generate_report', is_flag=True, default=False, help="Generate report and possibly send email to admins, etc.")
@click.option('--mode', type=click.Choice(['daemon', 'web', 'console']), default='console', help="Mode: daemon, web, console")
@click.option('--ooni', type=int, help="OONI Probe Data set range")
@click.option('--missing', type=click.Choice(type_choice + ['domain']), help="Get missing for alternative type or domain - use 'domain' or 'cloudfront', '")

def automation(testing, domain, test, proxy, existing, delete, domain_list, mirror_list, log,
    mirror_type, replace, nogithub, remove, report, mode, num, generate_report, s3, ooni, missing):
    configs = get_configs()
    logger.debug(f"Repo: {configs['repo']}")
    if domain:
        if delete:
            delete = delete_domain(domain, nogithub)
            if mode == 'console':
                if not delete:
                    print(f"Domain {domain} not deleted from github.")
                else:
                    print(f"Domain {domain} deleted from github, and {delete}")
        elif replace:
            delete_deprecated(domain)
            replace_mirror(domain=domain, existing=existing, replace=replace, nogithub=nogithub, mirror_type=mirror_type, mode=mode)
        elif remove:
            delete_deprecated(domain)
            removed = remove_mirror(domain=domain, remove=remove, nogithub=nogithub)
            if mode == 'console':
                print(removed)
        elif log:
            add_logging(domain=domain, mirror_type=mirror_type, mode=mode)
        elif s3:
            s3_storage_add = add_s3_storage(domain=domain, s3=s3)
            if mode == 'console':
                print (f"Result: {s3_storage_add}")
        elif mirror_type or existing:
            domain = strip_www(domain)
            delete_deprecated(domain,)
            new_add(domain=domain, mirror_type=mirror_type, nogithub=nogithub, existing=existing, mode=mode)
            domain_testing(proxy, mode, domain)
        elif report:
            domain_reporting(domain=domain, mode=mode)
        elif missing:
            missing_mirrors(domain=domain)
        else:
            domain_data = mirror_detail(domain=domain, proxy=proxy, mode=mode, test=test)
            if mode == 'console':
                if not domain_data:
                    print("No data returned!")
            return

    elif missing:
        missing_mirrors(missing=missing)
    elif ooni:
        get_ooni_data(ooni)
    elif testing:
        if mode == 'console':
            test = input("Test all (Y/n)?")
        else:
            test = 'y'
        if test.lower() != 'n':
            domain_testing(proxy, mode, '')
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

def domain_testing(proxy, mode, chosen_domain):
    """
    Tests domains, mirrors and onions in repo
    """
    mirror_list = domain_list()
    for domain in mirror_list['sites']:
        if ((not chosen_domain) or (chosen_domain == domain['main_domain'])):
            domain_data = mirror_detail(domain=domain['main_domain'], proxy=proxy, mode=mode, test=True)
            reporting = send_report(domain_data, mode)
            delete_deprecated(domain)
            if mode =='console':
                print(f"Reported? {reporting}")
        else:
            continue
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
    print(f"Preexisting: {exists}, current Alternatives: {domain_data['available_alternatives']}")
    
    if not exists:
        print("Domain doesn't exist!")
        return False
    elif nogithub:
        print("You said you wanted to delete a domain, but you also said no to github. Bye!")
        return False
    else:
        removed = remove_domain(domain)

    return removed

def replace_mirror(**kwargs):
    """
    Replace Mirror or Onion
    :kwarg <domain>
    :kwarg <replace>
    :kwarg [existing]
    :kwarg [mirror_type]
    :kwarg [nogithub]
    :kwarg [mode]
    :returns True or False
    """
    mode = kwargs['mode']
    if mode == 'console':
        print(f"Replacing mirror for: {kwargs['domain']}...")
    domain_data = check(kwargs['domain'])
    exists = domain_data['exists'] 
    current_alternatives = domain_data['available_alternatives']
    if not exists:
        if mode == 'console':
            print("Domain doesn't exist!")
        return False

    if 'mirror_type' not in kwargs:
        if mode == 'console':
            print("Need mirror type here!!")
        return False

    if kwargs['mirror_type'] == 'onion':
        proto = 'tor'
        mtype = 'eotk'
    elif kwargs['mirror_type'] == 'mirror':
        proto = 'http'
        mtype = 'mirror'
    elif kwargs['mirror_type'] == 'cloudfront':
        proto = 'https'
        mtype = 'proxy'
    else:
        proto = 'https'
        mtype = 'proxy'

    if 'existing' in kwargs and kwargs['existing']: # replacing with existing...
        if 'nogithub' in kwargs and kwargs['nogithub']:
            if mode == 'console':
                print("You wanted to replace with existing but didn't want it added to github! Bye!")
            return False
        domain_listing = add(domain=kwargs['domain'], 
                             mirror=kwargs['existing'], 
                             pre=exists,
                             replace=kwargs['replace'],
                             proto=proto,
                             mtype=mtype,
                             mode=mode
                            )
    else: # need to create a new mirror from the old automatically
        if kwargs['mirror_type'] == 'cloudfront':
            mirror = cloudfront_replace(kwargs['domain'], kwargs['replace'])
            domain_listing = add(domain=kwargs['domain'],
                                 mirror=mirror,
                                 pre=exists,
                                 replace=kwargs['replace'],
                                 proto=proto,
                                 mtype=mtype,
                                 mode=mode)
        else:
            if mode == 'console':
                print("Sorry, only cloudfront is automated!!")
                return False
    return True

def new_add(**kwargs):
    """
    Add new domain, mirror, onion or ipfs
    :kwarg <domain>
    :kwarg <mirror_type>
    :kwarg [existing]
    :kwarg [nogithub]
    :kwarg [mode]
    :returns True or False
    """
    mirror = ""
    domain_data = check(kwargs['domain'])
    if 'exists' not in domain_data:
        exists = False
    else:
        exists = domain_data['exists']
    if 'available_alternatives' in domain_data:
        current_alternatives = domain_data['available_alternatives']
    else:
        current_alternatives = []
    if 'mode' in kwargs and kwargs['mode'] == 'console':
        print(f"Preexisting: {exists}, current alternatives {current_alternatives}")
        print(f"Adding entry to {kwargs['mirror_type']} ...")
    else:
        kwargs['mode'] = 'web'

    if kwargs['mirror_type'] == 'cloudfront':
        proto = 'https'
        mtype = 'proxy'
        if kwargs['existing']:
            mirror = kwargs['existing']
        else:
            mirror = cloudfront_add(domain=kwargs['domain'], mode=kwargs['mode'])
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
            return "failed: Need to include existing url!"
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
            return "failed: You didn't include URL - mirror type needs that!"
        mirror = kwargs['existing']
    else:
        print("Need to define type of mirror. Use --mirror_type=cloudfront/azure/fastly/onion/mirror/ipfs")
        return "failed: Need to define type of mirror. Use --mirror_type=cloudfront/azure/fastly/onion/mirror/ipfs"

    if not mirror:
        print(f"Sorry, mirror not created for {kwargs['domain']}!")
        return "failed: Sorry, mirror not created!"

    replace = False
   
    if kwargs['nogithub']:
        print(f"You added this mirror: {mirror}. But no changes were made to github")
        return False
    else:
        domain_listing = add(domain=kwargs['domain'], mirror=mirror, pre=exists, proto=proto, mtype=mtype, mode=kwargs['mode'])
        return mirror

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
