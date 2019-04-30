"""
Automation of Creation of CDN and...

version 0.1
"""
import configparser
from proxy_utilities import cdn
#from add_to_repo import add

if __name__ == '__main__':

    while True:
        domain = input("Domain to add to distribution?")
        print("Adding distribution...")
        cdn(domain=domain)
        print("Adding to GitHub...")
        #add(domain=domain)
