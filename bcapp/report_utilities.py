import datetime
import logging
import os
import re
import socket
import datetime
import sqlalchemy as db
import pandas as pd
from proxy_utilities import get_configs

logger = logging.getLogger('logger')

def lists():

    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    domains = db.Table('domains', metadata, autoload=True, autoload_with=engine)
    mirrors = db.Table('mirrors', metadata, autoload=True, autoload_with=engine)

    # First, get domains and mirrors for matching

    domains_list = []
    query = db.select([domains])
    result = connection.execute(query).fetchall()

    for line in result:
        domains_list.append({'id' : line[0], 'name' : line[1]})

    mirrors_list = []
    query = db.select([mirrors])
    result = connection.execute(query).fetchall()
    for line in result:
        mirrors_list.append({'id' : line[0], 'mirror_url' : line[1], 'domain_id' : line[2]})
 
    return (domains_list, mirrors_list)

def reports(domain_id):
    """
    Gets all reports for a specific domain id
    :arg: domain
    :returns: all reports for a domain
    """
    # Get reports:
    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    reports = db.Table('reports', metadata, autoload=True, autoload_with=engine)
    query = db.select([reports]).where(reports.c.domain_id==domain_id)
    result = connection.execute(query).fetchall()

    print(result)

    return

def domain_reporting(**kwargs):
    """
    Report for domain
    :arg kwargs
    :kwarg domain
    :kwarg mode
    :returns ?
    """
    (domains_list, mirrors_list) = lists()

    if 'www.' in kwargs['domain']:
        domain = re.sub('www.', '', kwargs['domain'])
    else:
        domain = kwargs['domain']

    print(f"Domain: {domain}")

    for list_domain in domains_list:
        if list_domain['name'] == domain:
            domain_id = list_domain['id']

    print(f"Domain ID: {domain_id}")
    reports(domain_id)

    return

def send_report(domain_data, mode):
    """
    Make a report to the database with
    console-generated tests
    :arg domain_data
    :returns nothing
    """

    logger.debug(f"Domain Data: {domain_data}")
    now = datetime.datetime.now()
    host_name = socket.gethostname()
    host_ip = socket.gethostbyname(host_name) 

    configs = get_configs()

    engine = db.create_engine(configs['database_url'])
    connection = engine.connect()
    metadata = db.MetaData()

    domains = db.Table('domains', metadata, autoload=True, autoload_with=engine)
    mirrors = db.Table('mirrors', metadata, autoload=True, autoload_with=engine)
    reports = db.Table('reports', metadata, autoload=True, autoload_with=engine)

    query = db.select([domains])
    result = connection.execute(query).fetchall()
    
    domain_id = False
    for entry in result:
        d_id, domain = entry
        if domain in domain_data['domain']:
            domain_id = d_id
    
    if not domain_id: # we've not seen it before, add it
        insert = domains.insert().values(domain=domain_data['domain'])
        result = connection.execute(insert)
        domain_id = result.inserted_primary_key
    
    # Add mirrors
    for current_mirror in domain_data['current_mirrors']:
        query = db.select([mirrors])
        result = connection.execute(query).fetchall()
        mirror_id = False
        for entry in result:
            m_id, m_url, d_id = entry
            if current_mirror == m_url:
                mirror_id = m_id

        if not mirror_id: # add it
            insert = mirrors.insert().values(mirror_url=current_mirror, domain_id=domain_id)
            result = connection.execute(insert)
            mirror_id = result.inserted_primary_key
        
        # Make report
        report_data = {
            'date_reported': now,
            'domain_id': domain_id,
            'mirror_id': mirror_id,
            'user_agent': f'BC APP {mode}',
            'domain_status': domain_data[domain_data['domain']],
            'mirror_status': domain_data[current_mirror],
            'ip': host_ip
        }
        insert = reports.insert().values(**report_data)
        result = connection.execute(insert)

    if 'current_onions' not in domain_data:
        return True

    onions = db.Table('onions', metadata, autoload=True, autoload_with=engine)
    onion_reports = db.Table('onion_reports', metadata, autoload=True, autoload_with=engine)

    query = db.select([onions])
    o_result = connection.execute(query).fetchall()

    # Do we have onions for this domain?
    onion_id = False
    for entry in o_result:
        o_id, d_id, onion = entry
        if d_id == domain_id: #we've got it
            onion_id = o_id
    
    for current_onion in domain_data['current_onions']:
        if not onion_id: # don't have it, need to add it
            insert = onions.insert().values(domain_id=domain_id, onion=current_onion)
            result = connection.execute(insert)
            onion_id = result.inserted_primary_key

        # Make report
        onion_report_data = {
            'date_reported': now,
            'domain_id': domain_id,
            'onion_id': onion_id,
            'user_agent': f'BC APP {mode}',
            'onion_status': domain_data[domain_data['domain']],
        }
        insert = onion_reports.insert().values(**onion_report_data)
        result = connection.execute(insert)
        logger.debug(f"Report insert Result: {result}")

    return True