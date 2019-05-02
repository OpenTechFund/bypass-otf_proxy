import json
import base64
from github import Github
from proxy_utilities import get_configs

def add(**kwargs):
    """
    function to add mirror to repository
    """
    configs = get_configs()

    if 'mirrors' not in kwargs or not kwargs['mirrors']:
        print("No mirrors defined!!")
        return 

    g = Github(configs['API_key'])

    repo = g.get_repo(configs['repo'])
    mirrors_object = repo.get_file_contents(configs['file'])
    mirrors_decoded = mirrors_object.decoded_content
    mirrors = json.loads(str(mirrors_decoded, "utf-8"))

    if not kwargs['pre']: # site is just a simple add
        sites_add = {
            "main_domain": kwargs['domain'],
            "available_mirrors": kwargs['mirrors']
        }
        mirrors['sites'].append(sites_add)
    else:
        for site in mirrors['sites']:
            if site['main_domain'] == kwargs['domain']:
                if not kwargs['add']:
                    site['available_mirrors'] = kwargs['mirrors']
                else:
                    site['available_mirrors'].extend(kwargs['mirrors'])

    new_mirrors = json.dumps(mirrors, indent=4)
    new_file = base64.b64encode(bytes(new_mirrors, 'utf-8'))
    print(f"New Mirrors: {new_mirrors}")
    if not kwargs['pre']:
        commit_msg = f"Updated with new site {kwargs['domain']} - generated from automation script"
    else:
        commit_msg = f"Updated {kwargs['domain']} with new mirror - generated from automation script"

    repo.update_file(
        configs['file'],
        commit_msg,
        new_mirrors,
        mirrors_object.sha
        )

    return
    