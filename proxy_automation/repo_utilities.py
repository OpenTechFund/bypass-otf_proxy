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

    if not kwargs['mirrors']:
        num = input("How many mirrors to add?")
        add_mirrors = []
        for i in range(0, int(num)):
            add_mirrors[i] = input(f"Mirror {i}?")
    else:
        add_mirrors = kwargs['mirrors']

    repo = g.get_repo(configs['repo'])
    mirrors_object = repo.get_file_contents(configs['file'])
    mirrors_decoded = mirrors_object.decoded_content
    mirrors = json.loads(str(mirrors_decoded, "utf-8"))
    new_mirrors = dict(mirrors) # copy mirrors

    if not kwargs['pre']: # site is just a simple add
        sites_add = {
            "main_domain": kwargs['domain'],
            "available_mirrors": add_mirrors
        }
        new_mirrors['sites'].append(sites_add)
        print(f"New Mirror: {sites_add}")
    else:
        for site in new_mirrors['sites']:
            if site['main_domain'] in kwargs['domain']:
                change = input(f"Change {site['main_domain']} (Y/n)?")
                if change.lower() == 'n':
                    continue
                if not kwargs['add']:
                    site['available_mirrors'] = add_mirrors
                else:
                    site['available_mirrors'].extend(add_mirrors)
                print(f"Revised Mirror: {site}")

    final_mirrors = json.dumps(new_mirrors, indent=4)
    new_file = base64.b64encode(bytes(final_mirrors, 'utf-8'))
    if not kwargs['pre']:
        commit_msg = f"Updated with new site {kwargs['domain']} - generated from automation script"
    else:
        commit_msg = f"Updated {kwargs['domain']} with new mirror - generated from automation script"

    repo.update_file(
        configs['file'],
        commit_msg,
        final_mirrors,
        mirrors_object.sha
        )

    return
    
def check(domain):
    """
    Function to check to see what mirrors exist on a domain
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
            return site['available_mirrors']
        
    return ['no mirrors']
