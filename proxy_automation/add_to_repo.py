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

    g = Github(configs['github_API_key'])

    repo = g.get_repo(configs['repo'])
    mirrors_object = repo.get_file_contents(configs['file'])
    mirrors_decoded = mirrors_object.decoded_content
    mirrors = json.loads(str(mirrors_decoded, "utf-8"))

    sites_add = {
        "main_domain": kwargs['domain'],
        "available_mirrors": mirrors
    }
    mirrors['sites'].append(sites_add)

    new_mirrors = json.dumps(mirrors, indent=4)
    new_file = base64.b64encode(bytes(new_mirrors, 'utf-8'))

    repo.update_file(kwargs['github_file'], "Updated with new site", new_mirrors, mirrors_object.sha)

    return
    