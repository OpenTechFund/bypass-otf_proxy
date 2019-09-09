import json
import base64
from github import Github
from proxy_utilities import get_configs

def add(**kwargs):
    """
    function to add mirror to repository
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
    mirrors_object = repo.get_file_contents(configs['file'])
    mirrors_decoded = mirrors_object.decoded_content
    mirrors = json.loads(str(mirrors_decoded, "utf-8"))
    new_mirrors = dict(mirrors) # copy mirrors

    if not kwargs['pre']: # site is just a simple add
        if add_mirrors:
            sites_add = {
                "main_domain": kwargs['domain'],
                "available_mirrors": add_new
            }
            new_mirrors['sites'].append(sites_add)
            print(f"New Mirror: {sites_add}")
        else:
            sites_add = {
                "main_domain": kwargs['domain'],
                "available_onions": add_new
            }
            new_mirrors['sites'].append(sites_add)
            print(f"New Mirror: {sites_add}")
    else:
        for site in new_mirrors['sites']:
            if site['main_domain'] in kwargs['domain']:
                change = input(f"Change {site['main_domain']} (Y/n)?")
                if change.lower() == 'n':
                    continue
                if add_mirrors:
                    if not kwargs['add']:
                        site['available_mirrors'] = add_new
                    else:
                        site['available_mirrors'].extend(add_new)
                    print(f"Revised Mirror: {site}")
                else:
                    if not kwargs['add']:
                        site['available_onions'] = add_new
                    else:
                        site['available_onions'].extend(add_new)
                    print(f"Revised Site: {site}")

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

    return
    
def check(domain):
    """
    Function to check to see what mirrors and onions exist on a domain
    :param domain
    :return list with current available mirrors
    """
    configs = get_configs()
    g = Github(configs['API_key'])

    repo = g.get_repo(configs['repo'])
    mirrors_object = repo.get_file_contents(configs['file'])
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
