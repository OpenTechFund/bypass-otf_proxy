"""
Automation of Proxy Creation

version 0.1
"""
import configparser
from proxy_utilities import create_log_group, delete_log_group, create_task

def new_proxy(**kwargs):
    """
    Create New Proxy domain
    """

    domain = input("Domain to Proxy?")
    log_prefix = input("Log Group Prefix ('/ecs/')?")
    if not log_prefix:
        log_prefix = '/ecs/'
    shortcut = input("<shortcut>.bypasscensorship.org Shortcut?")
    
    # create CloudWatch log group
    log_group = log_prefix + shortcut
    confirm = input(f"Create log group {log_group} (Y/n)?")
    if confirm.lower() != 'n':
        create_log_group(log_group)

    # Create new task definition in ECS
    confirm = input(f"Create new task definition for {shortcut} (Y/n)?")
    if confirm.lower() != 'n':
        create_task(
            shortcut=shortcut,
            domain=domain,
            log_group=log_group            
        )

    # Create new service



    # Create Cloudwatch Alarm



if __name__ == '__main__':

    while True:
        print("""
        
        Options: 
        new: create new proxy
        lp: list proxies
        ll: list log groups
        q: quit
        
        """)

        option = input("Choice (new)>")

        if (not option) or option == 'new':
            new_proxy()
        elif option == 'lp':
            list_proxies()
        elif option == 'll':
            list_log_groups()
        elif option == 'q':
            quit()
        else:
            print("What??")
 



