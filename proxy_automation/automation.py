"""
Automation of Creation of CDN and...

version 0.3
"""
import sys
import configparser
from aws_utils import cloudfront, ecs
from repo_utilities import add, check, domain_list
from mirror_tests import domain_testing
from fastly_add import fastly_add
from azure_cdn import azure_add
import click

@click.command()
@click.option('--testing', is_flag=True, default=False, help="Domain testing of available mirrors")
@click.option('--domain', help="Domain to add/change to mirror list", type=str)
@click.option('--existing', type=str, help="Mirror exists already, just add to github.")
@click.option('--delete_domain', is_flag=True, default=False, help="Delete a domain from list")
@click.option('--domain_list', is_flag=True, default=False, help="List all domains and mirrors/onions")
@click.option('--add_new', is_flag=True, default=True, help="Add new domain or mirror (default)")
@click.option('--mirror_type', type=click.Choice(['cloudfront', 'azure', 'ecs', 'fastly', 'onion']), help="Type of mirror")
@click.option('--replace', is_flag=True, default=False, help="Replace a mirror/onion for domain")
@click.option('--github', is_flag=True, default=True, help="Add to github (default)")

def automation(testing, domain, existing, delete_domain, domain_list,
    add_new, mirror_type, replace, github):
    if domain:
        if add_new:
            new_add(domain=domain, mirror_type=mirror_type, github=github, existing=existing)
        elif delete_domain:
            delete_domain(domain, github)
        elif replace:
            replace_mirror(domain, github)
        else:
            print("Haven't defined enough to take action!")
            return
    else:
        if testing:
            domain_testing()
        if domain_list:
            dlist = domain_list()
            print(f""" List of all domains, mirrors and onions
            ___________________________________________________
            {dlist}
            ___________________________________________________
            """)
    
    return
        
def delete_domain(domain, github):
    """
    Delete domain
    :arg domain
    :arg github
    :returns nothing
    """
    print(f"delete {domain}")
    return

def replace_domain(domain, github):
    """
    Replace Mirror or Onion
    :arg domain
    :arg github
    :returns nothing
    """
    print(f"Replace mirror for: {domain}")
    return

def new_add(**kwargs):
    """
    Add new domain, mirror or onion
    :kwarg <domain>
    :kwarg <mirror_type>
    :kwarg [existing]
    :kwarg [github]
    :returns nothing
    """
    mirror = ""
    exists, current_mirrors, current_onions = check(domain)
    print(f"Preexisting: {exists}, current Mirrors: {current_mirrors}, current onions: {current_onions}")
    if not kwargs['existing']: #New domain and/or mirror
        pre_exist = False
        print(f"Adding distribution to {kwargs['mirror_type']} ...")
        if kwargs['mirror_type'] == 'cloudfront':
            mirror = cloudfront(domain=kwargs['domain'])
        elif kwargs['mirror_type'] == 'azure':
            mirror = azure_add(domain=kwargs['domain'])
        elif kwargs['mirror_type'] == 'ecs':
            mirror = ecs(domain=kwargs['domain'])
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
        elif not github:
            print(f"Mirror {mirror} added, but not added to Github as per your instructions!")
            return
    else: #adding existing mirror/onion
        if not kwargs['github']:
            print(f"You asked to add an existing mirror but then didn't want it added to github! Bye!")
            return
        mirror = kwargs['existing']
        pre_exist = True
        
    domain_listing = add(domain=kwargs['domain'], mirror=mirror, pre=pre_exist)
    print(f"New Domain listing: {domain_listing}")
    return

if __name__ == '__main__':
    automation()
