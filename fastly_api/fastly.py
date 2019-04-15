"""
Fastly Service Automation

"""
import os
import sys
import configparser
sys.path.insert(0, 'fastly-py')
import fastly

if __name__ == '__main__':
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
        count += 1
    domain = input("Domain to add?")
    service_target = input("Service to add it to?")
    fastly_domain = input("Fastly domain name?")
    target_service = services_list[service_target]

    #First step, clone version
    #version = api.version(args.service_id, args.version_id)

