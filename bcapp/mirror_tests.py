import json
import re
import base64
from github import Github
import requests
import urllib3
from requests_html import HTMLSession
from proxy_utilities import get_configs
from repo_utilities import check

def test_domain(domain, proxy):
    """
    Get response code from domain
    :param domain
    :returns status code (int)
    """
    https_domain = 'https://' + domain
    http_domain = 'http://' + domain
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    if proxy:
        print(f"Using proxy: {proxy}...")
        if 'https' in proxy:
            request_proxy = { 'https' : proxy}
        else:
            request_proxy = { 'http': proxy}
    try:
        if proxy:
            response = requests.get(https_domain, proxies=request_proxy)
        else:
            response = requests.get(https_domain)
        response_return = response.status_code
        response_url = response.url
    except Exception as e:
        try:
            if proxy:
                response = requests.get(http_domain, proxies=request_proxy)
            else:
                response = requests.get(http_domain)
            response_return = response.status_code
            response_url = response.url
        except Exception as e:
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
        
    return r.status_code, full_onion

def mirror_detail(**kwargs):
    """
    List and test mirrors for a domain
    :arg kwargs:
    :kwarg domain
    :kwarg proxy
    :kwarg mode
    :returns: json with data
    """
    output = {}
    domain = kwargs['domain']
    if kwargs['mode'] == 'console':
        print(f"Listing and Testing {domain}...")
    output['domain'] = domain
    exists, current_mirrors, current_onions = check(domain)
    if not exists:
        if kwargs['mode'] == 'console':
            print(f"{domain} doesn't exist in the mirror list.")
        output['exists'] = "False"
        return
    if kwargs['mode'] == 'console':  
        print(f"Mirror list: {current_mirrors} Onions: {current_onions}")

    output['current_mirrors'] = current_mirrors
    output['current_onions'] = current_onions

    mresp, murl = test_domain(domain, kwargs['proxy'])
    if kwargs['mode'] == 'console':
        print(f"Response code on domain: {mresp}, url: {murl}")
    output[domain] = mresp
    if current_mirrors:
        for mirror in current_mirrors:
            mresp, murl = test_domain(mirror, kwargs['proxy'])
            if kwargs['mode'] == 'console':
                print(f"Response code on mirror: {mresp}, url: {murl}")
            output[mirror] = mresp
    if current_onions:
        for onion in current_onions:
            mresp, murl = test_onion(onion)
            if kwargs['mode'] == 'console':
                print(f"Onion {onion}... Response code: {mresp} ... URL: {murl}")
            output[onion] = mresp

    return output

def domain_testing(testing, proxy):
    """
    Tests domains, mirrors and onions in repo
    """
    configs = get_configs()
    g = Github(configs['API_key'])
    repo = g.get_repo(configs['repo'])
    print(f"Repo: {repo} Configs: {configs}")
    mirrors_object = repo.get_contents(configs['file'])
    mirrors_decoded = mirrors_object.decoded_content
    mirrors = json.loads(str(mirrors_decoded, "utf-8"))
    errors = 0
    domains = 0
    domain_errors = 0
    error_domains = {}
    error_mirrors = []
    content_links = {}
    mirrors_without_one_good = []
    domains_with_onions = []
    for domain in mirrors['sites']:
        domains += 1
        if testing == 'domains':
            print(f"Testing domain: {domain['main_domain']}...")
            response, url = test_domain(domain['main_domain'], proxy)
            print(f"Domain {domain['main_domain']}... Response code: {response}")
            if int(response/100) != 2: # some sort of error happened
                error_domains[domain['main_domain']] = response
                domain_errors += 1
            continue
        print(f"Testing mirrors for domain: {domain['main_domain']}...")
        one_good_mirror = False
        has_onion = False
        if testing == 'noonions':
            for mirror in domain['available_mirrors']:
                has_error = False
                mresp, murl = test_domain(mirror, proxy)
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
        elif testing == 'onions':
            has_error = False
            if 'available_onions' in domain:
                for onion in domain['available_onions']:
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
                    else:
                        one_good_mirror = True
            else:
                print("No onions.")
        else: #testing onions, but domain has no onions
            print(f"{domain['main_domain']} has no available onions.")
            has_error = False
        if has_error:
            errors += 1
        if not one_good_mirror:
            mirrors_without_one_good.append(domain)
        if has_onion:
            domains_with_onions.append(domain)

    if testing == 'domains':
        print("Domains with errors: ")
        print(error_domains)
    else:
        print("Mirrors with errors: ")
        print(error_mirrors)
        print(f"{errors} out of {domains} domains have errors in mirrors or onions")
        if testing == 'noonions':
            print(f"{len(mirrors_without_one_good)} domains without one good mirror:")
        elif testing == 'onions':
            print(f"{len(mirrors_without_one_good)} domains without one good onion:")
        else: # testing domains
            print(f"{error_domains} domains have errors.")
        
        print(mirrors_without_one_good)

    return
