import json
import re
import base64
from github import Github
import requests
import urllib3
import logging
from requests_html import HTMLSession
from system_utilities import get_configs
from repo_utilities import check, delete_deprecated

logger = logging.getLogger('logger')

def test_domain(domain, proxy, mode, proto):
    """
    Get response code from domain
    :param domain
    :returns status code (int)
    """
    if 'http' not in domain:
        https_domain = 'https://' + domain
        http_domain = 'http://' + domain
    else:
        if 'https' in domain:
            https_domain = domain
            http_domain = False
        else:
            http_domain = domain
            https_domain = False

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    logger.debug(f"Testing {domain}...")
    if proxy:
        logger.debug(f"Using proxy: {proxy}...")
        if 'https' in proxy:
            request_proxy = { 'https' : proxy}
        else:
            request_proxy = { 'http': proxy}
    if https_domain:
        try:
            if proxy:
                response = requests.get(https_domain, proxies=request_proxy)
            elif https_domain:
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
    else:
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
    logger.debug(f"Testing {onion}...")
    try:
        r = session.get(onion, verify=False)
    except:
        return 500, onion
        
    return r.status_code, onion

def mirror_detail(**kwargs):
    """
    List and test mirrors for a domain
    :arg kwargs:
    :kwarg domain
    :kwarg proxy
    :kwarg mode
    :kwarg test
    :returns: json with data
    """
    output = {}
    domain = kwargs['domain']
    logger.debug(f"Listing {domain}...")
    output['domain'] = domain
    domain_data = check(domain)
    exists = domain_data['exists']
    if exists:
        current_alternatives = domain_data['available_alternatives']
    else:
        logger.debug(f"{domain} doesn't exist in the mirror list.")
        return False
    if kwargs['mode'] == 'console':  
        print(f"Alternatives: {current_alternatives}")

    if ('test' in kwargs) and (kwargs['test']):
        logger.debug(f"Testing {domain}...")
        mresp, murl = test_domain(domain, kwargs['proxy'], kwargs['mode'], '')
        if kwargs['mode'] == 'console':
            print(f"Response code on domain: {mresp}, url: {murl}")
        output[domain] = mresp

        output['current_alternatives'] = current_alternatives
        for alternative in current_alternatives:
            if alternative['proto'] == 'http' or alternative['proto'] == 'https':
                mresp, murl = test_domain(alternative['url'], kwargs['proxy'], kwargs['mode'], alternative['proto'])
                if kwargs['mode'] == 'console':
                    print(f"Response code on mirror: {mresp}, url: {murl}")
                alternative['result'] = mresp
            elif alternative['proto'] == 'tor':
                mresp, murl = test_onion(alternative['url'], kwargs['mode'])
                if kwargs['mode'] == 'console':
                    print(f"Onion {alternative['url']}... Response code: {mresp} ... URL: {murl}")
                alternative['result'] = mresp
            elif alternative['proto'] == 'ipfs':
                pass
            else:
                pass
        
        delete_deprecated(domain)
    else:
        output = "Not Tested."

    return output

