"""
Automation of Creation of CDN and...

version 0.2
"""
import sys
import configparser
from aws_utils import cloudfront, ecs
from repo_utilities import add, check
from mirror_tests import domain_testing
from fastly_add import fastly_add
from azure_cdn import azure_add

def domain_changes():
    while True:
        domain = input("Domain to change (return to quit)?")
        if not domain:
            quit()
        else:
            exists, current_mirrors, current_onions = check(domain)
            print(f"Preexisting: {exists}, current Mirrors: {current_mirrors}, current onions: {current_onions}")
    return

if __name__ == '__main__':

    action = input(f"Domain distribution/mirror, Testing of mirrors or mirror changes (D/t/c)?")
    if action.lower() == 't':
        domain_testing()
    elif action.lower() == 'c':
        domain_changes()
    else:
        while True:
            domain = input("Domain to add to distribution (return to quit)?")
            if not domain:
                quit()
            else:
                exists, current_mirrors, current_onions = check(domain)
                print(f"Preexisting: {exists}, current Mirrors: {current_mirrors}, current onions: {current_onions}")

            services = ['cloudfront', 'azure', 'ecs/docker'] # took out 'fastly' since we can't add any more mirrors there.
            mirrors = []
            for service in services:
                add_service = input(f"Add {service} mirror (y/N)?")
                if add_service.lower() != 'y':
                    continue
                print(f"Adding distribution to {service} ...")
                if service == 'cloudfront':
                    mirror = cloudfront(domain=domain)
                    print(f"AWS Cloudfront Mirror: {mirror}")
                    if mirror:
                        mirrors.append(mirror)
                if service == 'fastly':
                    mirror = fastly_add(domain=domain)
                    if mirror:
                        mirrors.append(mirror)
                if service == 'azure':
                    mirror = azure_add(domain=domain)
                    if mirror:
                        mirrors.append(mirror)
                if service == 'ecs/docker':
                    mirror = ecs(domain=domain)
                    if mirror:
                        mirrors.append(mirror)
                
            github = input(f"Add {domain} to GitHub (Y/n)?")
            if github.lower() == 'n':
                continue
            if not exists:
                pre_exist = False
                addm = False
                skip = False
            else:
                pre_exist = True
                addm = input("Add to or replace mirrors (or skip if just adding onions) (A/r/s)?")
                if addm.lower() == 'r':
                    addm = False
                elif addm.lower() == 's':
                    skip = True
                else:
                    addm = True
                    skip = False
            if not skip:
                if not mirrors:
                    num = int(input("Number of mirrors?"))
                    for i in range(0,num):
                        mirror = input('Mirror Site?')
                        mirrors.append(mirror)
                print("Adding to GitHub...")
                add(domain=domain, mirrors=mirrors, pre=pre_exist, add=addm)
                exists = True

            onion = input(f"Add onions to {domain} (y/N)?")
            if onion.lower() != 'y':
                continue
            onions = []
            if not exists:
                pre_exist = False
                addo = False
            else:
                pre_exist = True
                addo = input("Add to or replace onions (A/r)?")
                if addo.lower() == 'r':
                    addo = False
                else:
                    addo = True
            num = int(input("Number of onions?"))
            for i in range(0,num):
                onion = input('Onion Site?')
                onions.append(onion)
            print("Adding to GitHub...")
            add(domain=domain, onions=onions, pre=pre_exist, add=addm)

