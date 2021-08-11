import json
import base64
import datetime
import re
import logging
from github import Github
import tldextract
from system_utilities import get_configs
import db_utilities 

logger = logging.getLogger('logger')

def domain_list():
    """
    Lists all domains in mirror
    :returns list of domains from mirror.
    """
    configs = get_configs()
    g = Github(configs['API_key'])
   
    repo = g.get_repo(configs['repo'])
    mirrors_object = repo.get_contents(configs['file'])
    mirrors_decoded = mirrors_object.decoded_content
    mirrors = json.loads(str(mirrors_decoded, "utf-8"))
    
    return mirrors

def check_mirror(mirror_url):
    """
    Checks repo to find whether this mirror still exists.
    """
    if not mirror_url:
        return False

    domains = domain_list()

    check = False
    for domain in domains['sites']:
        if ('available_alternatives' in domain) and (domain['available_alternatives']):
            for alt in domain['available_alternatives']:
                if mirror_url == alt['url']:
                    check = True
    
    return check

def remove_domain(domain):
    """
    Remove a domain from repository
    :arg <domain>
    :returns False or True
    """
    mirrors = domain_list()
    for mirror in mirrors['sites']:
        if domain == mirror['main_domain']:
            remove = input(f"Remove {mirror['main_domain']} (y/N)?")
            if remove.lower() != 'y':
                return False
            mirrors['sites'].remove(mirror)
            commit_msg = f"Updated to remove domain {domain} - generated from automation script"
            final_mirrors = json.dumps(mirrors, indent=4)
            saved = save_mirrors(final_mirrors, commit_msg)
            if saved:
                # Add inactive in database
                inactive = db_utilities.set_domain_inactive(domain)
                if inactive:
                    return "Set to inactive in database!"
                else:
                    return "No such domain in DB!"
            else:
                return False

def remove_mirror(**kwargs):
    """
    Removes a mirror or onion from a domain listing
    :arg kwargs:<domain>
    :arg kwargs:<remove>
    """
    mirrors = domain_list()
    for domain in mirrors['sites']:
        if kwargs['domain'] == domain['main_domain']:
            domain['available_alternatives'] = [x for x in domain['available_alternatives'] if x['url'] != kwargs['remove']]
            print(f"New listing: {domain}")
    
    commit_msg = f"Removing {kwargs['remove']} from listing - generated automatically by script"

    final_mirrors = json.dumps(mirrors, indent=4)
    saved = save_mirrors(final_mirrors, commit_msg)
    if saved:
        # Add inactive in database
        inactive = db_utilities.set_alternative_inactive(kwargs['remove'])
        if inactive:
            return "Removed and set to inactive in Database!"
        else:
            return "No such alternative in DB!"
    else:
        return "Didn't save in GitHub"

def save_mirrors(new_mirrors, commit_msg):
    configs = get_configs()
    g = Github(configs['API_key'])
   
    repo = g.get_repo(configs['repo'])
    mirrors_object = repo.get_contents(configs['file'])
    old_mirrors_decoded = mirrors_object.decoded_content
    old_mirrors = json.loads(str(old_mirrors_decoded, "utf-8"))
    new_mirrors_encoded = json.loads(new_mirrors)
    if old_mirrors != new_mirrors_encoded:

        result = repo.update_file(
                    configs['file'],
                    commit_msg,
                    new_mirrors,
                    mirrors_object.sha
                    )

        print(f"Repo Result: {result}")
        if 'commit' in result:
            return True
        else:
            return False
    else:
        print("Nothing saved! Mirrors unchanged!")
        return False

def add(**kwargs):
    """
    function to add mirror to repository
    """
    quiet = False
    if 'quiet' in kwargs and kwargs['quiet']:
        quiet = True
    if 'mode' in kwargs and kwargs['mode'] != 'console':
        quiet = True

    now = str(datetime.datetime.now())
    mirrors = domain_list()
    new_mirrors = dict(mirrors) # copy mirrors
    if 'replace' in kwargs and kwargs['replace']:
        replace = True
    else:
        replace = False

    if not kwargs['pre']: # site is just a simple add
        site = {
            "main_domain": kwargs['domain'],
            "available_alternatives": [
                {
                    "proto": kwargs['proto'],
                    "type": kwargs['mtype'],
                    "created_at": now,
                    "url": kwargs['mirror']
                }
            ]
        }
        new_mirrors['sites'].append(site)
        if not quiet:
            print(f"New Mirror: {site}")
        site_add = site
    else:
        for site in new_mirrors['sites']:
            # TODO More robust matching
            if ((site['main_domain'] == kwargs['domain']) or
            ('www.' + site['main_domain'] == kwargs['domain']) or
            ('www.' + kwargs['domain'] == site['main_domain'])):
                if not quiet:
                    change = input(f"Change {site['main_domain']} (Y/n)?")
                    if change.lower() == 'n':
                        site_add = site
                        continue
                if not replace:
                    new_alternative = {
                        "proto": kwargs['proto'],
                        "type": kwargs['mtype'],
                        "created_at": now,
                        "url": kwargs['mirror']
                    }
                    site['available_alternatives'].append(new_alternative)
                else:
                    replacing = False
                    for alternative in site['available_alternatives']:
                        if kwargs['replace'] == alternative['url']:
                            logger.debug("Found it!")
                            replacing = True
                            alternative['url'] = kwargs['mirror']
                            alternative['updated_at'] = now
                    if not replacing:
                        logger.debug("No replacement found. No changes happened.")
                    
                    if not quiet:
                        print(f"Revised Site: {site}")
                
                site_add = site
    if replace and (not replacing):
        return site_add
    
    final_mirrors = json.dumps(new_mirrors, indent=4)
    if not kwargs['pre']:
        commit_msg = f"Updated with new site {kwargs['domain']} - generated from automation script"
    else:
        commit_msg = f"Updated {kwargs['domain']} with new mirror or onion - generated from automation script"
    result = save_mirrors(final_mirrors, commit_msg)
    
    return site_add
    
def site_match(main_domain, url):
    """
    Matching domain and URL
    """
    if (not main_domain) or (not url):
        return False
    if (main_domain == url):
        return True
    tld_extract = tldextract.extract(url)
    tld = tld_extract.domain + '.' + tld_extract.suffix
    full_domain = tld_extract.subdomain + '.' + tld
    if main_domain == full_domain:
        return True
    elif 'www.' + tld == main_domain:
        return True
    elif ((tld_extract.subdomain == 'www') and
        (tld == main_domain)):
        return True
    else:
        return False

def strip_www(domain):
    """
    Stripping any leading 'www.' from domain names
    """
    tld_extract = tldextract.extract(domain)
    if tld_extract.subdomain == 'www':
        stripped_domain = tld_extract.domain + '.' + tld_extract.suffix
        return stripped_domain
    else:
        return domain
            
def check(url):
    """
    Function to check to see what mirrors, nodes, and onions exist on a domain
    :param url
    :return list with current available mirrors
    """
    configs = get_configs()
    g = Github(configs['API_key'])

    repo = g.get_repo(configs['repo'])
    mirrors_object = repo.get_contents(configs['file'])
    mirrors_decoded = mirrors_object.decoded_content
    mirrors = json.loads(str(mirrors_decoded, "utf-8"))

    for site in mirrors['sites']:
        if site_match(site['main_domain'], url):
            exists = True
            if 'available_mirrors' in site:
                available_mirrors = site['available_mirrors']
            else:
                available_mirrors = []

            if 'available_onions' in site:
                available_onions = site['available_onions']
            else:
                available_onions = []

            if 'available_ipfs_nodes' in site:
                available_ipfs_nodes = site['available_ipfs_nodes']
            else:
                available_ipfs_nodes = []
            
            if 'available_alternatives' in site:
                available_alternatives = site['available_alternatives']
            else:
                available_alternatives = []

            return {
                'main_domain': site['main_domain'],
                'requested_url': url,
                'exists': exists,
                'available_mirrors': available_mirrors,
                'available_onions': available_onions,
                'available_ipfs_nodes': available_ipfs_nodes,
                'available_alternatives': available_alternatives
            }

    # No match       
    return {"exists": False, "alternatives" : 'None'}

def delete_deprecated(domain_data):
    """
    Delete deprecated keys
    """
    changed = False
    if 'available_mirrors' in domain_data:
        del domain_data['available_mirrors']
        changed = True
    if 'available_onions' in domain_data:
        del domain_data['available_onions']
        changed = True
    if 'available_ipfs_nodes' in domain_data:
        del domain_data['available_ipfs_nodes']
        changed = True

    if changed:
        mirrors = domain_list()
        for mirror in mirrors['sites']:
            if domain_data['main_domain'] == mirror['main_domain']:
                mirrors['sites'].remove(mirror)
                mirrors['sites'].append(domain_data)
        commit_msg = f"Updated to delete deprecated keys from {domain_data['main_domain']} - generated from automation script"
        final_mirrors = json.dumps(mirrors, indent=4)
        saved = save_mirrors(final_mirrors, commit_msg)
        if saved:
            return True
        else:
            return False
    else:
        return False

def edit_domain_in_repo(old_domain, new_domain):
    """
    Edit the repo listing for a domain
    """
    
    mirrors = domain_list()
    print(f"Old {old_domain} New: {new_domain}")
    change = False
    for mirror in mirrors['sites']:
        if mirror['main_domain'] == old_domain:
            mirror['main_domain'] = new_domain
            change = True
            print(mirror)
    
    if change:
        final_mirrors = json.dumps(mirrors, indent=4)
        saved = save_mirrors(final_mirrors, f"Editing {old_domain} to {new_domain}")
        if saved:
            return True
        else:
            return False

def missing_mirrors(**kwargs):
    """
    Find domains without certain alternatives
    If domain is supplied, return list of types not included
    If type is supplied, return list of domains without that type
    args: kwargs
    kwarg: [type]
    kwarg: [domain]
    """
    logger.debug(f"Finding missing mirrors...")
    
    domains = domain_list()
    if 'domain' in kwargs:
        search = 'domain'
    elif 'missing' in kwargs:
        search = 'type'
    else:
        return False

    logger.debug(f"Search {search}")
    missing_list = []
    for domain in domains['sites']:
        if 'available_alternatives' not in domain:
            continue
        if ((search == 'domain') and (kwargs['domain'] == domain['main_domain'])):
            missing = domain_missing(domain['available_alternatives'])
            return missing

        elif search == 'type': #search for missing domains
            missing = domain_missing(domain['available_alternatives'])
            if kwargs['missing'] in missing:
                missing_list.append(domain['main_domain'])
    logger.debug(f"Missing: {missing_list}")
    return missing_list

def domain_missing(alternatives):
    """
    finding missing alternatives in each domain
    """
    alt_types = [
        'cloudfront',
        'fastly',
        'azure',
        'onion',
        'mirror',
        'ipfs'
    ]
    found = []
    for alternative in alternatives:
        for alt_type in alt_types:
            if alternative['proto'] == 'tor':
                found.append('onion')
            elif alternative['type'] == 'proxy':
                if 'fastly' in alternative['url']:
                    found.append('fastly')
                elif 'cloudfront' in alternative['url']:
                    found.append('cloudfront')
                elif 'azureedge' in alternative['url']:
                    found.append('azure')
            elif alternative['type'] == 'mirror':
                found.append('mirror')
            elif alternative['type'] == 'ipfs':
                found.append('ipfs')

    missing = list(set(alt_types) - set(found))
    return missing
