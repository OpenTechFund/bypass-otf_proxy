"""
Utilities
"""
import configparser

def get_configs():
    """
    Gets configs from file
    :params none
    :returns dict with configs
    """
    # Read configs
    config = configparser.ConfigParser()
    
    try:
        config.read('auto.cfg')
    except configparser.Error:
        print('Config File not found or not readable!')
        quit()

    configs = {
        'profile': config.get('AWS', 'profile'),
        'region': config.get('AWS', 'region'),
        'repo': config.get('GITHUB', 'repo'),
        'API_key': config.get('GITHUB', 'API_key'),
        'file': config.get('GITHUB', 'file'),
        'azure_sub_id': config.get('AZURE', 'subscription_id'),
        'azure_tenant_id': config.get('AZURE', 'tenant_id'),
        'azure_app': config.get('AZURE', 'service_principal_app'),
        'azure_key': config.get('AZURE', 'service_principal_key')
    }

    return configs
