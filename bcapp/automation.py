"""
Automation of Creation of CDN and...

version 0.3
"""
import sys
import configparser
from aws_utils import cloudfront_add, ecs_add, cloudfront_replace, ecs_replace
from repo_utilities import add, check, domain_list, remove_domain, remove_mirror
from mirror_tests import domain_testing, mirror_detail
from fastly_add import fastly_add, fastly_replace
from azure_cdn import azure_add, azure_replace
import click

@click.command()
@click.option('--testing', type=click.Choice(['onions', 'noonions', 'domains']),
    help="Domain testing of available mirrors - choose onions, noonions, or domains")
@click.option('--domain', help="Domain to add/change to mirror list", type=str)
@click.option('--proxy', type=str, help="Proxy server to use for testing/domain detail.")
@click.option('--existing', type=str, help="Mirror exists already, just add to github.")
@click.option('--replace', type=str, help="Mirror/onion to replace.")
@click.option('--delete', is_flag=True, default=False, help="Delete a domain from list")
@click.option('--remove', type=str, help="Mirror or onion to remove")
@click.option('--domain_list', is_flag=True, default=False, help="List all domains and mirrors/onions")
@click.option('--mirror_list', is_flag=True, help="List mirrors for domain")
@click.option('--mirror_type', type=click.Choice(['cloudfront', 'azure', 'ecs', 'fastly', 'onion']), help="Type of mirror")
@click.option('--nogithub', is_flag=True, default=False, help="Do not add to github")

def automation(testing, domain, proxy, existing, delete, domain_list, mirror_list,
    mirror_type, replace, nogithub, remove):
    if domain:
        if delete:
            delete_domain(domain, nogithub)
        elif replace:
            replace_mirror(domain=domain, existing=existing, replace=replace, nogithub=nogithub, mirror_type=mirror_type)
        elif mirror_type or existing:
            new_add(domain=domain, mirror_type=mirror_type, nogithub=nogithub, existing=existing)
        elif remove:
            remove_mirror(domain=domain, remove=remove, nogithub=nogithub)
        else:
            if proxy:
                mirror_detail(domain, proxy, False)
            else:
                mirror_detail(domain, False, False)
    else:
        if testing:
            if proxy:
                domain_testing(testing, proxy)
            else:
                domain_testing(testing, False)
        if domain_list:
            dlist = domain_list()
            print(f""" List of all domains, mirrors and onions
            ___________________________________________________
            {dlist}
            ___________________________________________________
            """)
    
    return

def delete_domain(domain, nogithub):
    """
    Delete domain
    :arg domain
    :arg nogithub
    :returns nothing
    """
    print(f"Deleting {domain}...")
    exists, current_mirrors, current_onions = check(domain)
    print(f"Preexisting: {exists}, current Mirrors: {current_mirrors}, current onions: {current_onions}")
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
    exists, current_mirrors, current_onions = check(kwargs['domain'])
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
        else: # need to create a new murror from the old
            if 'mirror_type' not in kwargs:
                print("Need to define --mirror_type=fastly/ecs/azure/cloudfront/onion")
                return
            if kwargs['mirror_type'] == 'fastly':
                mirror = fastly_replace(kwargs['domain'], kwargs['replace'])
            elif kwargs['mirror_type'] == 'cloudfront':
                mirror = cloudfront_replace(kwargs['domain'], kwargs['replace'])
            elif kwargs['mirror_type'] == 'ecs':
                mirror = ecs_replace(kwargs['domain'], kwargs['replace'])
            elif kwargs['mirror_type'] == 'azure':
                mirror = azure_replace(kwargs['domain'], kwargs['replace'])
            elif kwargs['mirror_type'] == 'onion':
                mirror = onion_add(kwargs['domain'], kwargs['replace'])
            else:
                print("Incorrect mirror definition! Must be one of: fastly/ecs/azure/cloudfront/onion")
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
    Add new domain, mirror or onion
    :kwarg <domain>
    :kwarg <mirror_type>
    :kwarg [existing]
    :kwarg [nogithub]
    :returns nothing
    """
    mirror = ""
    exists, current_mirrors, current_onions = check(kwargs['domain'])
    print(f"Preexisting: {exists}, current Mirrors: {current_mirrors}, current onions: {current_onions}")
    if not kwargs['existing']: #New mirror
        print(f"Adding distribution to {kwargs['mirror_type']} ...")
        if kwargs['mirror_type'] == 'cloudfront':
            mirror = cloudfront_add(domain=kwargs['domain'])
        elif kwargs['mirror_type'] == 'azure':
            mirror = azure_add(domain=kwargs['domain'])
        elif kwargs['mirror_type'] == 'ecs':
            mirror = ecs_add(domain=kwargs['domain'])
        elif kwargs['mirror_type'] == 'fastly':
            mirror = fastly_add(domain=kwargs['domain'])
        elif kwargs['mirror_type'] == 'onion':
            mirror = onion_add(domain=kwargs['domain'])
        else:
            print("Need to define type of mirror. Use --mirror_type=cloudfront/azure/ecs/fastly/onion")
            return
        if not mirror:
            print(f"Sorry, mirror not created for {kwargs['domain']}!")
            return
        elif kwargs['nogithub']:
            print(f"Mirror {mirror} added, but not added to Github as per your instructions!")
            return
        replace = False
    else: #adding existing mirror/onion
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
    automation()
