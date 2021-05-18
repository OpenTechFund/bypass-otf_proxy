"""
Utilities for connection 
with database
"""
import os
import logging
from dotenv import load_dotenv
import sqlalchemy as db
from system_utilities import get_configs

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
        d_id, domain_fetched, ext_ignore, paths_ignore, s3_bucket, azure_profile = entry
        if domain_fetched in domain:
            domain_data['id'] = d_id
            domain_data['ext_ignore'] = ext_ignore
            domain_data['paths_ignore'] = paths_ignore
            domain_data['s3_bucket'] = s3_bucket
            domain_data['azure_profile'] = azure_profile
    
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
