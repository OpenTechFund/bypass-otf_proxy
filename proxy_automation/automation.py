"""
Automation of Creation of CDN and...

version 0.1
"""
import configparser
from proxy_utilities import cdn
from add_to_repo import add

if __name__ == '__main__':

    while True:
        domain = input("Domain to add to distribution?")
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
            else:
                pre_exist = True
            addm = input("Add to or replace mirrors (A/r)?")
            if addm.lower() == 'r':
                addm = False
            else:
                addm = True
            num = int(input("Number of mirrors?"))
            mirrors = []
            for i in range(0,num):
                mirror = input('Mirror Site?')
                mirrors.append(mirror)
            print("Adding to GitHub...")
            add(domain=domain, mirrors=mirrors, pre=pre_exist, add=addm)
        