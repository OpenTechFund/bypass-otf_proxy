import json
import re
import base64
from github import Github
import requests
from requests_html import HTMLSession
from proxy_utilities import get_configs

def test_domain(domain):
    """
    Get response code from domain
    :param domain
    :returns status code (int)
    """
    https_domain = 'https://' + domain
    http_domain = 'http://' + domain
    try:
        response = requests.get(https_domain)
        response_return = response.status_code
    except requests.exceptions.SSLError:
        response = requests.get(http_domain)
        response_return = response.status_code
        
    return response_return

def check_domain_content(**kwargs):
    """
    finds if the domain is found in the links in the page
    :param kwargs: <domain>
    :param kwargs: <mirror>
    :returns number of links (domain is found) or 0 (no domain is found)
    """
    session = HTMLSession()
    mirror = 'https://' + kwargs['mirror']
    response = session.get(mirror)
    instances = 0
    for link in response.html.links:
        if re.search(kwargs['domain'], link):
            instances += 1
    return instances

def domain_testing():
    """
    Tests all domains and mirrors in repo
    """
    configs = get_configs()
    g = Github(configs['API_key'])
    repo = g.get_repo(configs['repo'])
    mirrors_object = repo.get_file_contents(configs['file'])
    mirrors_decoded = mirrors_object.decoded_content
    mirrors = json.loads(str(mirrors_decoded, "utf-8"))

    error_domains = {}
    error_mirrors = []
    content_links = {}
    for domain in mirrors['sites']:
        print(f"Testing domain: {domain['main_domain']}...")
        response = test_domain(domain['main_domain'])
        print(f"Domain {domain['main_domain']}... Response code: {response}")
        if int(response/100) != 2: # some sort of error happened
            error_domains[domain['main_domain']] = response
        for mirror in domain['available_mirrors']:
            mresp = test_domain(mirror)
            domain_content = check_domain_content(mirror=mirror, domain=domain['main_domain'])
            print(f"Mirror {mirror}... Response code: {mresp}, Domain Content: {domain_content}")
            if (int(mresp/100) != 2): # some sort of error happened
                error = {
                    "main_domain": domain['main_domain'],
                    "error_mirror": mirror,
                    "domain_content": domain_content
                }
                error_mirrors.append(error)

    print("Domains with errors: ")
    print(error_domains)
    print("Mirrors with errors: ")
    print(error_mirrors)

    return