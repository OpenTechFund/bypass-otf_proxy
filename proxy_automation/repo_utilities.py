import json
import base64
from github import Github
from proxy_utilities import get_configs

def domain_list():
    """
    Lists all domains in mirror
    :returns list of domains from mirror.
    """
    configs = get_configs()
    g = Github(configs['API_key'])

    if 'mirrors' in kwargs:
        add_new = kwargs['mirrors']
        add_mirrors = True
    if 'onions' in kwargs:
        add_new = kwargs['onions']
        add_mirrors = False
   
    repo = g.get_repo(configs['repo'])
    mirrors_object = repo.get_contents(configs['file'])
    mirrors_decoded = mirrors_object.decoded_content
    mirrors = json.loads(str(mirrors_decoded, "utf-8"))
    
    return mirrors

def add(**kwargs):
    """
    function to add mirror to repository
    """
    configs = get_configs()
    g = Github(configs['API_key'])
   
    repo = g.get_repo(configs['repo'])
    mirrors_object = repo.get_contents(configs['file'])
    mirrors_decoded = mirrors_object.decoded_content
    mirrors = json.loads(str(mirrors_decoded, "utf-8"))
    new_mirrors = dict(mirrors) # copy mirrors

    if not kwargs['pre']: # site is just a simple add
        if '.onion' not in kwargs['mirror']: # mirror not onion
            site = {
                "main_domain": kwargs['domain'],
                "available_mirrors": kwargs['mirror']
            }
            new_mirrors['sites'].append(site)
            print(f"New Mirror: {site}")
        else: # onion not mirror
            site = {
                "main_domain": kwargs['domain'],
                "available_onions": kwargs['mirror']
            }
            new_mirrors['sites'].append(site)
            print(f"New Mirror: {site}")
        site_add = site
    else:
        for site in new_mirrors['sites']:
            if site['main_domain'] in kwargs['domain']:
                change = input(f"Change {site['main_domain']} (Y/n)?")
                if change.lower() == 'n':
                    continue
                if '.onion' not in kwargs['mirror'][0]: # mirror not onion
                    if 'available_mirrors' in site:
                        site['available_mirrors'].extend(kwargs['mirror'])
                    else:
                        site['available_mirrors'] = kwargs['mirror']
                    print(f"Revised Mirror: {site}")
                else: # onion not mirror
                    if 'available_onions' in site:
                        site['available_onions'].extend(kwargs['mirror'])
                    else:
                        site['available_onions'] = kwargs['mirror']
                    print(f"Revised Site: {site}")
                site_add = site

    final_mirrors = json.dumps(new_mirrors, indent=4)
    new_file = base64.b64encode(bytes(final_mirrors, 'utf-8'))
    if not kwargs['pre']:
        commit_msg = f"Updated with new site {kwargs['domain']} - generated from automation script"
    else:
        commit_msg = f"Updated {kwargs['domain']} with new mirror or onion - generated from automation script"

    repo.update_file(
        configs['file'],
        commit_msg,
        final_mirrors,
        mirrors_object.sha
        )

    return site_add
    
def check(domain):
    """
    Function to check to see what mirrors and onions exist on a domain
    :param domain
    :return list with current available mirrors
    """
    configs = get_configs()
    g = Github(configs['API_key'])

    repo = g.get_repo(configs['repo'])
    mirrors_object = repo.get_contents(configs['file'])
    mirrors_decoded = mirrors_object.decoded_content
    mirrors = json.loads(str(mirrors_decoded, "utf-8"))

    for site in mirrors['sites']:
        if ((site['main_domain'] == domain) or
            ('www.' + site['main_domain'] == domain)):
            exists = True
            if 'available_mirrors' in site:
                available_mirrors = site['available_mirrors']
            else:
                available_mirrors = []
            if 'available_onions' in site:
                available_onions = site['available_onions']
            else:
                available_onions = []
            return exists, available_mirrors, available_onions
            
    return False, [], []
