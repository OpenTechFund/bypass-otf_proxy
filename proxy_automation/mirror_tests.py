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

def test_onion(onion):
    session = requests.session()
    session.proxies = {
        'http': 'socks5h://localhost:9050',
        'https': 'socks5h://localhost:9050'
        }
    full_onion = 'https://' + onion
    try:
        r = session.get(full_onion, verify=False)
    except:
        print("TOR not properly configured!")
        return 500, full_onion
        
    return r.status_code, full_domain

def domain_testing():
    """
    Tests domains, mirrors and onions in repo
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
    domains_with_onions = []
    tdom = input("Test Domains (y/N)?")
    if tdom.lower() == 'y':
        tdomains = True
    else:
        tdomains = False
    wtt = input("Test All, No onions, or Just onions (A/n/j/q)?")
    if wtt.lower() == 'q':
        return
    elif wtt.lower() == 'n':
        no_onions = True
    elif wtt.lower() == 'j':
        just_onions = True
        no_onions = False
    else:
        just_onions = False
        no_onions = False
    for domain in mirrors['sites']:
        domains += 1
        print(f"Testing domain: {domain['main_domain']}...")
        if tdomains:
            response, url = test_domain(domain['main_domain'])
            print(f"Domain {domain['main_domain']}... Response code: {response}")
            if int(response/100) != 2: # some sort of error happened
                error_domains[domain['main_domain']] = response
        one_good_mirror = False
        if not just_onions:
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
        if not no_onions and 'available_onions' in domain:
            has_onion = False
            for onion in domain['available_onions']:
                has_error = False
                has_onion = True
                mresp, murl = test_onion(onion)
                print(f"Onion {onion}... Response code: {mresp} ... URL: {murl}")
                if (int(mresp/100) != 2):
                    error = {
                        "main_domain": domain['main_domain'],
                        "error_onion": onion,
                        "response_code": mresp,
                        "url": murl
                    }
                    error_mirrors.append(error)
                    has_error = True
        if has_error:
            errors += 1
        if not one_good_mirror:
            mirrors_without_one_good.append(domain)
        if has_onion:
            domains_with_onions.append(domain)

    print("Domains with errors: ")
    print(error_domains)
    print("Mirrors with errors: ")
    print(error_mirrors)
    print(f"{errors} out of {domains} domains have errors")
    if not just_onions:
        print("Domains without one good mirror:")
        print(mirrors_without_one_good)

    return
