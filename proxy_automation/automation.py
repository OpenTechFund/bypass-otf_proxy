"""
Automation of Creation of CDN and...

version 0.1
"""
import configparser
from proxy_utilities import cdn
from add_to_repo import add
from mirror_tests import domain_testing

if __name__ == '__main__':

    action = input(f"Domain distribution/mirror or Testing of mirrors (D/t)?")
    if action.lower() == 't':
        domain_testing()
    else:
        while True:
            domain = input("Domain to add to distribution (return to quit)?")
            if not domain:
                quit()
            option = input("Cloudfront, GitHub, or both? (c/g/B)?")
            if not option:
                option = 'b'
            if option.lower() == 'c' or option.lower() == 'b':
                services = ['cloudfront']
                for service in services:
                    print(f"Adding distribution... to {service} ...")
                    mirror = cdn(domain=domain, service=service)
                    print(f"AWS Cloudfront Mirror: {mirror}")
            if option.lower() == 'g' or option.lower() == 'b':
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
                mirrors = []
                if mirror:
                    mirrors.append(mirror)
                else:
                    num = int(input("Number of mirrors?"))
                    for i in range(0,num):
                        mirror = input('Mirror Site?')
                        mirrors.append(mirror)
                print("Adding to GitHub...")
                add(domain=domain, mirrors=mirrors, pre=pre_exist, add=addm)
        