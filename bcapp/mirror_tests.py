import json
import re
import base64
from github import Github
import requests
import urllib3
from requests_html import HTMLSession
from proxy_utilities import get_configs
from repo_utilities import check

def test_domain(domain, proxy, mode):
    """
    Get response code from domain
    :param domain
    :returns status code (int)
    """
    https_domain = 'https://' + domain
    http_domain = 'http://' + domain
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    if mode == 'console':
        print(f"Testing {domain}...")
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

def test_onion(onion, mode):
    session = requests.session()
    session.proxies = {
        'http': 'socks5h://localhost:9050',
        'https': 'socks5h://localhost:9050'
        }
    full_onion = 'https://' + onion
    if mode == 'console':
        print(f"Testing {onion}...")
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

    mresp, murl = test_domain(domain, kwargs['proxy'], kwargs['mode'])
    if kwargs['mode'] == 'console':
        print(f"Response code on domain: {mresp}, url: {murl}")
    output[domain] = mresp
    if current_mirrors:
        for mirror in current_mirrors:
            mresp, murl = test_domain(mirror, kwargs['proxy'], kwargs['mode'])
            if kwargs['mode'] == 'console':
                print(f"Response code on mirror: {mresp}, url: {murl}")
            output[mirror] = mresp
    if current_onions:
        for onion in current_onions:
            mresp, murl = test_onion(onion, kwargs['mode'])
            if kwargs['mode'] == 'console':
                print(f"Onion {onion}... Response code: {mresp} ... URL: {murl}")
            output[onion] = mresp

    return output

