"""
Fastly Service Automation

"""
import os
import sys
import configparser
sys.path.insert(0, 'fastly-py')
import fastly

def fastly_add(**kwargs):
    print("Getting configs...")
    # Set environment variables fastly needs from config file
    config = configparser.ConfigParser()
    CONFIG_FILE = 'fastly.cfg'
    try:
        config.read(CONFIG_FILE)
    except (IOError, OSError):
        print('Config File not found or not readable!')
        quit()

    fastly_user = config.get('FASTLY', 'FASTLY_USER')
    os.environ['FASTLY_USER'] = fastly_user
    fastly_api_key = config.get('FASTLY', 'FASTLY_API_KEY')
    fastly_host = config.get('FASTLY', 'FASTLY_HOST')
    os.environ['FASTLY_HOST'] = fastly_host
    fastly_secure = config.get('FASTLY', 'FASTLY_SECURE')
    os.environ['FASTLY_SECURE'] = fastly_secure
    fastly_password = config.get('FASTLY', 'FASTLY_PASSWORD')
    os.environ['FASTLY_PASSWORD'] = fastly_password

    # login
    api = fastly.API()
    api.authenticate_by_key(fastly_api_key)

    # list services
    services_list = api.services()
    print ("List of current services:")
    count = 0
    for service in services_list:
        svc = vars(service)['_original_attrs']
        print (f"{count}: {svc['name']} [{svc['id']}] Version {svc['version']}")
         # list backends
        backends = api.backends(svc['id'], svc['version'])
        print(f"Number of Backends: {len(backends)}")
        for backend in backends:
            backend_vars = vars(backend)
            print(f"Backend: {backend_vars['_original_attrs']['hostname']}")
        count += 1
    domain = kwargs['domain']
    service_target = input(f"Service to add {domain} to?")
    fastly_subdomain = domain[0:5] + '1'
    fastly_domain_confirm = input(f"Fastly subdomain ({fastly_subdomain}.global.ssl.fastly.net)?")
    if fastly_domain_confirm:
        fastly_subdomain = fastly_domain_confirm
    fastly_domain = fastly_subdomain + '.global.ssl.fastly.net'
    # Clone version
    target_service = services_list[int(service_target)]
    target_service_vars = vars(services_list[int(service_target)])['_original_attrs']
    version = api.version(target_service_vars['id'], target_service_vars['version'])
    new_version = int(target_service_vars['version']) + 1
    clone = input("Need to clone a new version (y/N)?")
    if clone.lower() == 'y':
        print("Cloning version...")
        version.clone()

    # Domain
    domain_add = input("Need to add a new domain (y/N)?")
    if domain_add.lower() == 'y':
        version = api.version(target_service_vars['id'], new_version)
        comment = input("Any comment?")
        version.domain(fastly_domain, comment)
    
    # Condition
    condition_add = input("Need to add a new condition (y/N)?")
    if condition_add.lower() == 'y':
        # Get the version object
        version = api.version(target_service_vars['id'], new_version)
        # add new condition
        condition_name = fastly_subdomain
        cond_statement = 'req.http.host ~ "' + fastly_domain + '"'
        print("Saving condition...")
        version.condition(name=condition_name, statement=cond_statement, type='REQUEST')
    else:
        condition_name = input(f"Name of current condition for {fastly_domain}?")
    # Header
    header_add = input("Need to add a new header (y/N)?")
    if header_add.lower() == 'y':
        version = api.version(target_service_vars['id'], new_version)
        header_name = fastly_subdomain
        src = '"' + domain + '"'
        version.header(
            name=header_name,
            type='REQUEST',
            dst='http.Host',
            src=src,
            priority='10',
            request_condition=condition_name
        )

    # Backend
    backend_add = input("Need a new origin (y/N)?")
    if backend_add.lower() == 'y':
        version = api.version(target_service_vars['id'], new_version)
        origin_name = fastly_subdomain
        version.backend(
            name=origin_name,
            hostname=domain,
            port='443',
            request_condition=condition_name,
            ssl_check_cert='false'
        )
    activate_version = input(f"Activate new version (y/N)?")
    if activate_version.lower() == 'y':
        print("Activating new version!")
        version = api.version(target_service_vars['id'], new_version)
        version.activate()

    return fastly_domain
        
def fastly_list():
    print("Getting configs...")
    # Set environment variables fastly needs from config file
    config = configparser.ConfigParser()
    CONFIG_FILE = 'fastly.cfg'
    try:
        config.read(CONFIG_FILE)
    except (IOError, OSError):
        print('Config File not found or not readable!')
        quit()

    fastly_user = config.get('FASTLY', 'FASTLY_USER')
    os.environ['FASTLY_USER'] = fastly_user
    fastly_api_key = config.get('FASTLY', 'FASTLY_API_KEY')
    fastly_host = config.get('FASTLY', 'FASTLY_HOST')
    os.environ['FASTLY_HOST'] = fastly_host
    fastly_secure = config.get('FASTLY', 'FASTLY_SECURE')
    os.environ['FASTLY_SECURE'] = fastly_secure
    fastly_password = config.get('FASTLY', 'FASTLY_PASSWORD')
    os.environ['FASTLY_PASSWORD'] = fastly_password

    # login
    api = fastly.API()
    api.authenticate_by_key(fastly_api_key)

    # list services
    services_list = api.services()
    print ("List of current services:")
    count = 0
    for service in services_list:
        svc = vars(service)['_original_attrs']
        print (f"{count}: {svc['name']} [{svc['id']}] Version {svc['version']}")
         # list backends
        backends = api.backends(svc['id'], svc['version'])
        print(f"Number of Backends: {len(backends)}")
        for backend in backends:
            backend_vars = vars(backend)
            print(f"Backend: {backend_vars['_original_attrs']['hostname']}")
        count += 1

def fastly_replace(domain, replace):
    """
    Replace fastly mirror
    """
    fastlylist = fastly_list()

    return