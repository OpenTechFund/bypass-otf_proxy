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
        'roleArn': config.get('AWS', 'roleArn'),
        'repo': config.get('GITHUB', 'repo'),
        'API_key': config.get('GITHUB', 'API_key'),
        'file': config.get('GITHUB', 'file'),
        'azure_sub_id': config.get('AZURE', 'subscription_id'),
        'azure_tenant_id': config.get('AZURE', 'tenant_id'),
        'azure_app': config.get('AZURE', 'service_principal_app'),
        'azure_key': config.get('AZURE', 'service_principal_key'),
        'mirror_docker_image': config.get('AWS', 'mirror_docker_image'),
        'ecs_log_group': config.get('AWS', 'ecs_log_group'),
        'subnet': config.get('AWS', 'subnet'),
        'vpc': config.get('AWS', 'vpc'),
        'security_group': config.get('AWS', 'security_group'),
        'paths': config.get('LOGS', 'path_file'),
        'log_storage_bucket': config.get('LOGS', 'log_storage_bucket'),
        'log_level': config.get('SYSTEM', 'log_level'),
        'local_tmp': config.get('SYSTEM', 'local_tmp'),
        'database_url': config.get('DATABASE', 'url')
    }

    return configs
