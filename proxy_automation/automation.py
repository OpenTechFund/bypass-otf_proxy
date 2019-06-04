"""
Automation of Creation of CDN and...

version 0.1
"""
import sys
import configparser
from proxy_utilities import cloudfront
from add_to_repo import add
from mirror_tests import domain_testing
from fastly_add import fastly_add

if __name__ == '__main__':

    action = input(f"Domain distribution/mirror or Testing of mirrors (D/t)?")
    if action.lower() == 't':
        domain_testing()
    else:
        while True:
            domain = input("Domain to add to distribution (return to quit)?")
            if not domain:
                quit()
            
            services = ['cloudfront', 'fastly']
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
                
            github = input(f"Add {domain} to GitHub (Y/n)?")
            if github.lower() == 'n':
                continue
            pre = input("Pre-existing (y/N)?")
            if pre.lower() != 'y':
                pre_exist = False
                addm = False
            else:
                pre_exist = True
                addm = input("Add to or replace mirrors (A/r)?")
                if addm.lower() == 'r':
                    addm = False
                else:
                    addm = True
            if not mirrors:
                num = int(input("Number of mirrors?"))
                for i in range(0,num):
                    mirror = input('Mirror Site?')
                    mirrors.append(mirror)
            print("Adding to GitHub...")
            add(domain=domain, mirrors=mirrors, pre=pre_exist, add=addm)
        