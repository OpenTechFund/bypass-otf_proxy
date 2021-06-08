import json
import base64
import datetime
import re
import logging
from github import Github
import tldextract
from system_utilities import get_configs
from db_utilities import set_domain_inactive, set_alternative_inactive

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
                inactive = set_domain_inactive(domain)
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
    :arg kwargs:<nogithub>
    """
    mirrors = domain_list()
    for domain in mirrors['sites']:
        if kwargs['domain'] == domain['main_domain']:
            domain['available_alternatives'] = [x for x in domain['available_alternatives'] if x['url'] != kwargs['remove']]
            print(f"New listing: {domain}")
    
    commit_msg = f"Removing {kwargs['remove']} from listing - generated automatically by script"

    if not kwargs['nogithub']:
        final_mirrors = json.dumps(mirrors, indent=4)
        saved = save_mirrors(final_mirrors, commit_msg)
        if saved:
            # Add inactive in database
            inactive = set_alternative_inactive(kwargs['remove'])
            if inactive:
                return "Removed and set to inactive in Database!"
            else:
                return "No such alternative in DB!"
        else:
            return "Didn't save in GitHub"
    else:
        print(f"Removed {kwargs['remove']} but didn't save!")
        return False

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
            if 'available_alternatives' in site:
                available_alternatives = site['available_alternatives']
            else:
                available_alternatives = []

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

def convert_all():
    """
    Convert all domains to v2
    """
    mirrors = domain_list()
    mirrors['version'] = '2.0'
    for domain in mirrors['sites']:
        converted_domain = convert_process(domain)
        if not converted_domain: #domain already converted!
            continue
        else:
            domain['available_alternatives'] = converted_domain
        print(f"New data for {domain['main_domain']}: {domain}")
    
    commit_msg = "Updated to convert all domains to v2 - generated from automation script"
    final_mirrors = json.dumps(mirrors, indent=4)
    saved = save_mirrors(final_mirrors, commit_msg)
    if saved:
        print("Converted!")
        return True
    else:
        print("Not Converted!")
        return False

def convert_process(domain_data):
    """
    The algorithm to convert the domain
    """
    configs = get_configs()
    ipfs_domain = configs['ipfs_domain']
    now = datetime.datetime.now()
    logger.debug(f"Old domain data: {domain_data}")
    ip_match = re.compile('[0-9]{1,3}[\.]{1}[0-9]{1,3}[\.]{1}[0-9]{1,3}[\.]{1}[0-9]{1,3}')
    proto_match = re.compile(':\/\/')
    if ('available_alternatives' not in domain_data) or (not domain_data['available_alternatives']):
        logger.debug("No alternatives.")
        available_alternatives = []
        if 'available_mirrors' in domain_data:
            for mirror in domain_data['available_mirrors']:
                alternative = {
                    'created_at': str(now),
                    'updated_at': str(now)
                }
                if ip_match.search(mirror): # it's an IP address, thus a mirror
                    alternative['type'] = 'mirror'
                    alternative['proto'] = 'http'
                    if not proto_match.search(mirror):
                        alternative['url'] = 'http://' + mirror
                    else:
                        alternative['url'] = mirror
                elif ('fastly' in mirror) or ('cloudfront' in mirror) or ('azureedge' in mirror):
                    alternative['type'] = 'proxy'
                    alternative['proto'] = 'https'
                    if not proto_match.search(mirror):
                        alternative['url'] = 'https://' + mirror
                    else:
                        alternative['url'] = mirror
                else:
                    alternative['type'] = 'unknown'
                    alternative['proto'] = 'https'
                    if not proto_match.search(mirror):
                        alternative['url'] = 'https://' + mirror
                    else:
                        alternative['url'] = mirror
                available_alternatives.append(alternative)
                logger.debug(f"Alternative: {alternative}")
        if 'available_onions' in domain_data:
            for onion in domain_data['available_onions']:
                alternative = {
                    'created_at': str(now),
                    'updated_at': str(now),
                    'proto': 'tor',
                    'type': 'eotk'
                }
                if not proto_match.search(onion):
                    alternative['url'] = 'https://' + onion
                else:
                    alternative['url'] = onion
                available_alternatives.append(alternative)
                logger.debug(f"Alternative: {alternative}")
        if 'available_ipfs_nodes' in domain_data:
            for ipfs_node in domain_data['available_ipfs_nodes']:
                alternative = {
                    'created_at': str(now),
                    'updated_at': str(now),
                    'proto': 'https',
                    'type': 'ipfs_node'
                }
                if not proto_match.search(ipfs_node):
                    alternative['url'] = 'https://' + ipfs_domain + ipfs_node
                else:
                    alternative['url'] = ipfs_node
                available_alternatives.append(alternative)
                logger.debug(f"Alternative: {alternative}")
        return available_alternatives
    else:
        logger.debug("Domain already converted!")
        return False # Domain already converted

def delete_deprecated(domain):
    """
    Delete deprecated keys
    """
    domain_data = check(domain)
    del domain_data['available_mirrors']
    del domain_data['available_onions']
    del domain_data['available_ipfs_nodes']

    mirrors = domain_list()
    for mirror in mirrors['sites']:
        if domain == mirror['main_domain']:
            mirrors['sites'].remove(mirror)
            mirrors['sites'].append(domain_data)
    commit_msg = f"Updated to delete deprecated keys from {domain} - generated from automation script"
    final_mirrors = json.dumps(mirrors, indent=4)
    saved = save_mirrors(final_mirrors, commit_msg)
    if saved:
        return True
    else:
        return False 


def convert_domain(domain, delete):
    """
    Convert domain from v1 to v2
    """
    configs = get_configs()
    domain_data = check(domain)
    if 'exists' not in domain_data:
        return
    logger.debug("Converting...")
    available_alternatives = convert_process(domain_data)
    if not available_alternatives:
        return

    domain_data['available_alternatives'] = available_alternatives
    logger.debug(f"New Domain Data: {domain_data}")

    mirrors = domain_list()
    for mirror in mirrors['sites']:
        print(f"Mirror: {mirror}")
        if domain == mirror['main_domain']:
            mirrors['sites'].remove(mirror)
            mirrors['sites'].append(domain_data)
    commit_msg = f"Updated to convert domain {domain} to v2 - generated from automation script"
    final_mirrors = json.dumps(mirrors, indent=4)
    saved = save_mirrors(final_mirrors, commit_msg)
    if saved:
        return True
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


    
