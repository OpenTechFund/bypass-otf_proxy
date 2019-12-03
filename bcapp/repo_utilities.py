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
   
    repo = g.get_repo(configs['repo'])
    mirrors_object = repo.get_contents(configs['file'])
    mirrors_decoded = mirrors_object.decoded_content
    mirrors = json.loads(str(mirrors_decoded, "utf-8"))
    
    return mirrors

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
            print(f"New Mirrors: {mirrors['sites']}")
            commit_msg = f"Updated to remove domain {domain} - generated from automation script"
            final_mirrors = json.dumps(mirrors, indent=4)
            saved = save_mirrors(final_mirrors, commit_msg)
            if saved:
                return True
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
            if '.onion' in kwargs['remove']:
                domain['available_onions'] = [x for x in domain['available_onions'] if x != kwargs['remove']]
            else:
                domain['available_mirrors'] = [x for x in domain['available_mirrors'] if x != kwargs['remove']]
            print(f"New listing: {domain}")
            commit_msg = f"Removing {kwargs['remove']} from listing - generated automatically by script"

    if not kwargs['nogithub']:
        final_mirrors = json.dumps(mirrors, indent=4)
        save_mirrors(final_mirrors, commit_msg)
    else:
        print(f"Removed {kwargs['remove']} but didn't save!")

    return

def save_mirrors(mirrors, commit_msg):
    configs = get_configs()
    g = Github(configs['API_key'])
   
    repo = g.get_repo(configs['repo'])
    mirrors_object = repo.get_contents(configs['file'])
    new_file = base64.b64encode(bytes(mirrors, 'utf-8'))

    result = repo.update_file(
                configs['file'],
                commit_msg,
                mirrors,
                mirrors_object.sha
                )

    if 'commit' in result:
        return True
    else:
        return False

def add(**kwargs):
    """
    function to add mirror to repository
    """
    mirrors = domain_list()
    new_mirrors = dict(mirrors) # copy mirrors
    if 'replace' in kwargs and kwargs['replace']:
        replace = True
    else:
        replace = False

    if 'quiet' in kwargs and kwargs['quiet']:
        quiet = True
    else:
        quiet = False

    if not kwargs['pre']: # site is just a simple add
        if '.onion' not in kwargs['mirror'][0]: # mirror not onion
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
            if ((site['main_domain'] == kwargs['domain']) or
            ('www.' + site['main_domain'] == kwargs['domain']) or
            ('www.' + kwargs['domain'] == site['main_domain'])):
                if not quiet:
                    change = input(f"Change {site['main_domain']} (Y/n)?")
                    if change.lower() == 'n':
                        site_add = site
                        continue
                if '.onion' not in kwargs['mirror'][0]: # mirror not onion
                    if 'available_mirrors' in site and not replace:
                        site['available_mirrors'].extend(kwargs['mirror'])
                    elif replace:
                        site['available_mirrors'] = [x if (x != kwargs['replace']) else kwargs['mirror'][0] for x in site['available_mirrors']]
                    else:
                        site['available_mirrors'] = kwargs['mirror']
                    if not quiet:
                        print(f"Revised Mirror: {site}")
                else: # onion not mirror
                    if 'available_onions' in site and not replace:
                        site['available_onions'].extend(kwargs['mirror'])
                    elif replace:
                        site['available_onions'] = [x if (x != kwargs['replace']) else kwargs['mirror'][0] for x in site['available_onions']]
                    else:
                        site['available_onions'] = kwargs['mirror']
                    if not quiet:
                        print(f"Revised Site: {site}")
                site_add = site

    final_mirrors = json.dumps(new_mirrors, indent=4)
    if not kwargs['pre']:
        commit_msg = f"Updated with new site {kwargs['domain']} - generated from automation script"
    else:
        commit_msg = f"Updated {kwargs['domain']} with new mirror or onion - generated from automation script"
    result = save_mirrors(final_mirrors, commit_msg)
    
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
            ('www.' + site['main_domain'] == domain) or
            ('www.' + domain == site['main_domain'])):
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
