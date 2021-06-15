import datetime
import logging
import os
import re
import gzip
import socket
import json
import datetime
from dotenv import load_dotenv
import sqlalchemy as db
from system_utilities import get_configs, send_email
from repo_utilities import site_match
import boto3

logger = logging.getLogger('logger')

def lists():

    load_dotenv()
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

def translate_reports(report):
    """
    Translates report from postgres into text for display or email
    """
    load_dotenv()
    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    domains = db.Table('domains', metadata, autoload=True, autoload_with=engine)
    mirrors = db.Table('mirrors', metadata, autoload=True, autoload_with=engine)
    domain_query = db.select([domains])
    domain_list = connection.execute(domain_query).fetchall()
    mirror_query = db.select([mirrors])
    mirror_list = connection.execute(mirror_query).fetchall()

    translated_report = f"Date Reported: {report['date_reported']} \n"
    translated_report += f"User Agent: {report['user_agent']} \n"
    for domain in domain_list:
        if report['domain_id'] == domain['id']:
            translated_report += f"Domain: {domain['domain']} Status: {report['domain_status']} \n"
    
    for mirror in mirror_list:
        if report['mirror_id'] == mirror['id']:
            translated_report += f"Mirror: {mirror['mirror_url']} Status: {report['mirror_status']} \n"

    return(translated_report)

def generate_admin_report(mode):
    """
    Generate a report with important data for the day - email if mode is daemon
    """
    logger.debug("Sending Admin Report...")
    yesterday = datetime.datetime.today() - datetime.timedelta(days=1)
    configs = get_configs()

    load_dotenv()
    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    reports = db.Table('reports', metadata, autoload=True, autoload_with=engine)
    report_query = db.select([reports]).where(reports.c.date_reported > yesterday)
    report_list = connection.execute(report_query).fetchall()

    important_reports = ""
    for report in report_list:
        logger.debug(f"Report: {report}")
        if ((report['domain_status'] != 200) or (report['mirror_status'] != 200)):
            translated_report = translate_reports(report)
            important_reports += translated_report

    if mode == 'daemon':
        if important_reports:
            message_to_send = f""" Reporting problematic Domains and/or Alternatives for Today: 

            {important_reports}
            """
        else:
            message_to_send = "No Problematic Domains or Alternatives for the day. Check system."

        users = db.Table('users', metadata, autoload=True, autoload_with=engine)
        user_query = db.select([users]).where(users.c.admin == True)
        user_list = connection.execute(user_query).fetchall()
        for user in user_list:
            if user['notifications'] and user['active']:
                email = send_email(
                            user['email'],
                            "Daily Report From BC APP",
                            message_to_send
                        )
                logger.debug(f"Message Sent to {user['email']}: {email}")

    else:
        if important_reports:
            print(f""" Here are the problematic domains and/or alternatives for Today: 

            {important_reports}
            """  ) 
        else:
            print("No problems reported today - check your crontab!")

    return


def send_report(domain_data, mode):
    """
    Make a report to the database with
    console-generated tests
    :arg domain_data
    :returns nothing
    """

    data_pretty = json.dumps(domain_data)
    logger.debug(f"Domain Data: {data_pretty}")
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
    inactive = False
    for entry in result:
        d_id, domain, ext, paths, s3_storage, azure_profile, inactive = entry
        logger.debug(f"Entry: {entry}")
        if domain in domain_data['domain']:
            domain_id = d_id
            if inactive:
                logger.debug("Inactive Domain!")
                return False
    
    logger.debug(f"Domain ID: {domain_id}")
    
    if not domain_id: # we've not seen it before, add it
        logger.debug("New Domain!")
        insert = domains.insert().values(domain=domain_data['domain'])
        result = connection.execute(insert)
        domain_id = result.inserted_primary_key[0]
        logger.debug(f"Domain ID: {domain_id}")
    
    # Add mirrors
    if (('current_alternatives' not in domain_data) or (not domain_data['current_alternatives'])):
        logger.debug("Not reporting on v1 data!")
        return False
    for current_alternative in domain_data['current_alternatives']:
        query = db.select([mirrors])
        result = connection.execute(query).fetchall()
        mirror_id = False
        for entry in result:
            m_id, m_url, d_id, proto, m_type, inactive = entry
            if current_alternative['url'] == m_url:
                mirror_id = m_id
        logger.debug(f"Mirror ID: {mirror_id}")

        if not mirror_id: # add it
            logger.debug("New Alternative!")
            insert = mirrors.insert().values(
                mirror_url=current_alternative['url'],
                domain_id=domain_id,
                mirror_type=current_alternative['type'],
                protocol=current_alternative['proto'])
            result = connection.execute(insert)
            mirror_id = result.inserted_primary_key[0]

            logger.debug(f"Mirror ID: {mirror_id}")
        
        # Make report
        report_data = {
            'date_reported': now,
            'domain_id': domain_id,
            'mirror_id': mirror_id,
            'user_agent': f'BC APP {mode}',
            'domain_status': domain_data[domain_data['domain']],
            'mirror_status': current_alternative['result'],
            'ip': host_ip
        }
        insert = reports.insert().values(**report_data)
        result = connection.execute(insert)

    return True
def get_ooni_data(range):
    """
    Get data from OONI S3 bucket
    """
    configs = get_configs()
    bucket = 'ooni-data-eu-fra'
    
    client = boto3.client('s3')
    #get date range
    now = datetime.datetime.now()
    then = now - datetime.timedelta(days=range)
    delta = datetime.timedelta(days=1)

    logger.debug(f"Now: {now} Then: {then}")

    engine = db.create_engine(configs['database_url'])
    connection = engine.connect()
    metadata = db.MetaData()

    ooni_reports = db.Table('ooni_reports', metadata, autoload=True, autoload_with=engine)

    file_list = []
    logger.debug("Getting OONI file list from S3...")
    while then <= now:
        date_str = then.strftime('%Y%m%d')
        file_date = 'raw/' + date_str
        then += delta

        date_report_list = client.list_objects_v2(
            Bucket=bucket,
            Prefix=file_date
        )

        for s3_file in date_report_list['Contents']:
            if ('webconnectivity' in s3_file['Key']) and ('jsonl' in s3_file['Key']):
                file_list.append(s3_file['Key'])


    # Process Files
    domain_list, mirror_list = lists()

    matching_domain_data = {}
    for domain in domain_list:
        matching_domain_data[domain['name']] = []

    for file in file_list:
        file_parts = file.split('/')
        local_name = ('-').join(file_parts)
        local_file_path = configs['local_tmp'] + '/' + local_name

        logger.debug(f"Downloading to: {local_file_path}")
        with open(local_file_path, 'wb') as file_data:
            client.download_fileobj(bucket, file, file_data)

        data = []
        
        with gzip.open(local_file_path) as raw_file:
            line = raw_file.readline()
            json_data = json.loads(line)
            data.append(json_data)

        os.remove(local_file_path)      
       
        for jdata in data:
            logger.debug(f"input: {jdata['input']}")
            domain_name = False
            for domain in domain_list:
                match = site_match(domain['name'], jdata['input'])
                if match:
                    domain_name = domain['name']
                    domain_id = domain['id']
            if not domain_name:
                logger.debug("No match.")
                continue
    
            date_reported = datetime.datetime.strptime(jdata['measurement_start_time'], '%Y-%m-%d %H:%M:%S')
            matching_domain_data[domain_name] = {
                'domain_id': domain_id,
                'url_accessed': jdata['input'],
                'country': jdata['probe_cc'],
                'blocked': jdata['test_keys']['blocking'],
                'dns_consistency': jdata['test_keys']['dns_consistency'],
                'date_reported': date_reported
            }       
            
            for key in jdata['test_keys']['requests']:
                for s_key in key:
                    if s_key == 'failure':
                        matching_domain_data[domain_name]['failure'] = key['failure']

            print(f"Matching Domain Data for {domain_name}:{matching_domain_data[domain_name]}")
            # Make report
            ooni_report_data = matching_domain_data[domain_name]

            insert = ooni_reports.insert().values(**ooni_report_data)
            result = connection.execute(insert)

    return
