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
        response_url = response.url
    except requests.exceptions.SSLError:
        response = requests.get(http_domain)
        response_return = response.status_code
        response_url = response.url
    except:
        print("Error!")
        return 500, ""
        
    return response_return, response_url

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

    errors = 0
    domains = 0
    error_domains = {}
    error_mirrors = []
    content_links = {}
    mirrors_without_one_good = []
    for domain in mirrors['sites']:
        domains += 1
        print(f"Testing domain: {domain['main_domain']}...")
        response, url = test_domain(domain['main_domain'])
        print(f"Domain {domain['main_domain']}... Response code: {response}")
        if int(response/100) != 2: # some sort of error happened
            error_domains[domain['main_domain']] = response
        one_good_mirror = False
        for mirror in domain['available_mirrors']:
            has_error = False
            mresp, murl = test_domain(mirror)
            print(f"Mirror {mirror}... Response code: {mresp} ... URL: {murl}")
            if (int(mresp/100) != 2) or (domain['main_domain'] in murl):
                error = {
                    "main_domain": domain['main_domain'],
                    "error_mirror": mirror,
                    "response_code": mresp,
                    "url": murl
                }
                error_mirrors.append(error)
                has_error = True
            else:
                one_good_mirror = True
        if has_error:
            errors += 1
        if not one_good_mirror:
            mirrors_without_one_good.append(domain)

    print("Domains with errors: ")
    print(error_domains)
    print("Mirrors with errors: ")
    print(error_mirrors)
    print(f"{errors} out of {domains} domains have errors")
    print("Domains without one good mirror:")
    print(mirrors_without_one_good)

    return