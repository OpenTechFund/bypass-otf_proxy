"""
Utilities for connection 
with database
"""
import os
import logging
import datetime
from dotenv import load_dotenv
import sqlalchemy as db
from system_utilities import get_configs
import repo_utilities

logger = logging.getLogger('logger')

def set_domain_inactive(del_domain):
    """
    When deleting a domain, set it inactive in the database
    """
    load_dotenv()

    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    domains = db.Table('domains', metadata, autoload=True, autoload_with=engine)

    update = domains.update().where(domains.c.domain == del_domain).values(inactive=True)
    connection.execute(update)

    logger.debug(f"Update: {update}")

    return True
    
def set_alternative_inactive(alternative):
    """
    When removing an alternative, set it to inactive in the database
    """
    load_dotenv()
    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    mirrors = db.Table('mirrors', metadata, autoload=True, autoload_with=engine)
    update = mirrors.update().where(mirrors.c.mirror_url == alternative).values(inactive=True)
    connection.execute(update)

    logger.debug(f"Update: {update}")

    return True

def get_mirror_url_from_id(id):
    """
    Get mirror URL from id
    """
    load_dotenv()
    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    mirrors = db.Table('mirrors', metadata, autoload=True, autoload_with=engine)
    query = db.select([mirrors]).where(mirrors.c.id == id)
    try:
        mirror_id, mirror_url, domain_id, mirror_type, protocol, inactive = connection.execute(query).fetchone()
    except:
        mirror_url = False

    return mirror_url

def get_domain_data(domain):
    """
    Get domain data
    """
    load_dotenv()

    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    domains = db.Table('domains', metadata, autoload=True, autoload_with=engine)

    ## Get domain id
    query = db.select([domains])
    result = connection.execute(query).fetchall()
    
    domain_data = {
        'id': False
    }
    for entry in result:
        d_id, domain_fetched, ext_ignore, paths_ignore, s3_bucket, azure_profile, inactive = entry
        if domain_fetched in domain:
            domain_data['id'] = d_id
            domain_data['ext_ignore'] = ext_ignore
            domain_data['paths_ignore'] = paths_ignore
            domain_data['s3_bucket'] = s3_bucket
            domain_data['azure_profile'] = azure_profile
            domain_data['inactive'] = inactive
    
    if not domain_data['id']: 
        domain_data = False

    return domain_data

def report_save(**kwargs):
    """
    Saving report to database
    """
    domain_data = get_domain_data(kwargs['domain'])
    if not domain_data:
        return False
    domain_id = domain_data['id']
    load_dotenv()

    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()
    log_reports = db.Table('log_reports', metadata, autoload=True, autoload_with=engine)

    # Save report
    report_data = {
            'date_of_report': kwargs['datetime'],
            'domain_id': domain_id,
            'report': kwargs['report_text'],
            'hits':kwargs['hits'],
            'home_page_hits':kwargs['home_page_hits'],
            'first_date_of_log':kwargs['first_date_of_log'],
            'last_date_of_log':kwargs['last_date_of_log'],
            'log_type':kwargs['log_type']
        }
    insert = log_reports.insert().values(**report_data)
    result = connection.execute(insert)
    report_id = result.inserted_primary_key[0]

    #logger.debug(f"Report ID: {report_id}")

    return

def cross_check(domain):
    """
    Making sure all domain alternatives have database entry
    """
    repo_list = repo_utilities.check(domain)
    load_dotenv()
    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    domains = db.Table('domains', metadata, autoload=True, autoload_with=engine)
    mirrors = db.Table('mirrors', metadata, autoload=True, autoload_with=engine)

    for alt in repo_list['available_alternatives']:
        query = db.select([mirrors]).where(mirrors.c.mirror_url==alt['url'])
        result = connection.execute(query)
        domain_row = result.fetchone()
        if domain_row == None:
            print("DIDN'T LIKE IT")
            query = db.select([domains]).where(domains.c.domain == domain)

            result = connection.execute(query)
            domain_row = result.fetchone()

            alternative = {
                'mirror_type': alt['type'],
                'mirror_url': alt['url'], 
                'domain_id': domain_row.id,
                'protocol': alt['proto']
            }
            insert = mirrors.insert().values(**alternative)
            result = connection.execute(insert)
        
    return repo_list

def get_sys_info(**kwargs):
    """
    Get system info from database
    :arg kwargs
    :kwarg request
    :kwarg [update]
    :kwarg [all]
    """
    load_dotenv()

    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    now = datetime.datetime.now()

    sys_settings = db.Table('system_settings', metadata, autoload=True, autoload_with=engine)
    query = db.select([sys_settings])
    sys_info = connection.execute(query).fetchone()

    if sys_info == None: # no rows have been saved so far
        system_info = {
            'last_email_report_sent': now,
            'last_ooni_report_generated': now,
            'last_logfile_analysis': now,
            'last_domain_test': now
        }
        insert = sys_settings.insert().values(**system_info)
        connection.execute(insert)
    else:
        a, b, c, d, e = sys_info
        system_info = {
            'id': a,
            'last_email_report_sent': b,
            'last_ooni_report_generated': c,
            'last_logfile_analysis': d,
            'last_domain_test': e
        }

    if ('update' in kwargs) and kwargs['update']: #update db with new data
        update_query = f"update system_settings set {kwargs['request']} = '{now}' where id = 1"
        connection.execute(update_query)

    if ('all' in kwargs) and kwargs['all']:
        return system_info
    else:
        return system_info[kwargs['request']]

