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
from db_utilities import get_sys_info
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

    translated_report = f"Date Reported: {report['date_reported']} "
    translated_report += f"User Agent: {report['user_agent']} "
    for domain in domain_list:
        if report['domain_id'] == domain['id']:
            translated_report += f"Domain: {domain['domain']} Status: {report['domain_status']} "
    
    for mirror in mirror_list:
        if report['mirror_id'] == mirror['id']:
            translated_report += f"Mirror: {mirror['mirror_url']} Status: {report['mirror_status']} "

    translated_report += '\n'

    return(translated_report)

def ooni_reports(date):
    """
    Get ooni report details
    :arg date
    """
    configs = get_configs()

    load_dotenv()
    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    ooni_reports = db.Table('ooni_reports', metadata, autoload=True, autoload_with=engine)
    query = f"select * from ooni_reports where date_reported > '{date}'"
    ooni_report_list = connection.execute(query).fetchall()

    number_of_ooni_reports = len(ooni_report_list)
    number_of_ooni_problems = 0
    ooni_problems = []
    for orep in ooni_report_list:
        if (((orep['blocked'] != 'false') and
            (orep['failure'] != None)) or
            (orep['dns_consistency'] == 'inconsistent')):
            oprob = {}
            number_of_ooni_problems += 1
            oprob['url_accessed'] = orep['url_accessed']
            oprob['country'] = orep['country']
            oprob['failure'] = orep['failure']
            oprob['dns_consistency'] = orep['dns_consistency']
            ooni_problems.append(oprob)

    return number_of_ooni_reports, number_of_ooni_problems, ooni_problems

def generate_admin_report(**kwargs):
    """
    Generate a report with important data - email if mode is daemon
    :arg kwargs
    :kwarg mode 
    :kwarg user_id (not used at this time)
    :returns nothing
    """
    logger.debug("Creating Admin Report...")
    configs = get_configs()

    load_dotenv()
    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    users = db.Table('users', metadata, autoload=True, autoload_with=engine)
    domains = db.Table('domains', metadata, autoload=True, autoload_with=engine)
    dgdomains = db.Table('dg_domains', metadata, autoload=True, autoload_with=engine)
    system_settings = db.Table('system_settings', metadata, autoload=True, autoload_with=engine)

    # System settings
    sys_query = db.select([system_settings])
    system_raw_dates = connection.execute(sys_query).fetchone()
    last_logfile_analysis = system_raw_dates['last_logfile_analysis'].strftime('%A %B %d, %Y at %I:%M %p %Z')
    last_ooni_report_generated = system_raw_dates['last_ooni_report_generated'].strftime('%A %B %d, %Y at %I:%M %p %Z')
    last_domain_test = system_raw_dates['last_domain_test'].strftime('%A %B %d, %Y at %I:%M %p %Z')


    # List admins
    user_query = db.select([users]).where(users.c.admin == True)
    admin_list = connection.execute(user_query).fetchall()

    # List Domain Group Owners
    # TODO: Generate reports for domain group owners
    dg_query = "select * from users, domain_groups where CAST(users.domain_group_id as integer)=domain_groups.id and domain_groups.name != 'None'"
    dg_list = connection.execute(dg_query).fetchall()

    # Get last date
    last_email_report_sent = get_sys_info(request='last_email_report_sent', update=True)
    
    reports = db.Table('reports', metadata, autoload=True, autoload_with=engine)
    report_query = db.select([reports]).where(reports.c.date_reported > last_email_report_sent)
    report_list = connection.execute(report_query).fetchall()

    important_reports = ""
    number_of_reports = len(report_list)
    number_of_problems = 0
    for report in report_list:
        if ((report['domain_status'] != 200) or (report['mirror_status'] != 200)):
            number_of_problems += 1
            translated_report = translate_reports(report)
            important_reports += translated_report

    number_of_ooni_reports, number_of_ooni_problems, ooni_problems = ooni_reports(last_email_report_sent)
    for problem in ooni_problems:
        orept = f"OONI: URL Accessed: {problem['url_accessed']} Kind of Failure: {problem['failure']} DNS Consistency: {problem['dns_consistency']}\n"
        important_reports += orept

    if kwargs['mode'] == 'daemon':
        if important_reports:
            message_to_send =  f""" Reporting problematic Domains and/or Alternatives since {last_email_report_sent}: 
            There were {number_of_reports} domain testing reports, and {number_of_problems} problems.

            There were {number_of_ooni_reports} reports from OONI, with {number_of_ooni_problems} of problems.

            The last domain test was {last_domain_test}.
            The last logfile analysis was done on {last_logfile_analysis}.
            and the last OONI report was generated on {last_ooni_report_generated}.

            All detailed problem reports are below:

            {important_reports}
        """        
        else:
            message_to_send = f"""No Problematic Domains or Alternatives since {last_email_report_sent}. 
            
            The last domain test was {last_domain_test}.
            The last logfile analysis was done on {last_logfile_analysis}.
            and the last OONI report was generated on {last_ooni_report_generated}.
            
            You might want to check the system."""
        
        for user in admin_list:
            if user['notifications'] and user['active']:
                email = send_email(
                            user['email'],
                            "Report From BC APP",
                            message_to_send
                        )
                logger.debug(f"Message Sent to {user['email']}: {email}")

    else:
        if important_reports:
            print(f""" Reporting problematic Domains and/or Alternatives for Today: 
            There were {number_of_reports} domain testing reports, and {number_of_problems} problems.

            There were {number_of_ooni_reports} reports from OONI, with {number_of_ooni_problems} of problems.

            The last domain test was {last_domain_test}.
            The last logfile analysis was done on {last_logfile_analysis}.
            The last OONI report was generated on {last_ooni_report_generated}.

            All detailed problem reports are below:

            {important_reports}
            """) 
        else:
            print(f"""No problems reported since {last_email_report_sent}.
            
            The last domain test was {last_domain_test}.
            The last logfile analysis was done on {last_logfile_analysis}.
            and the last OONI report was generated on {last_ooni_report_generated}.
            
            You might want to check the system.""")

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
    
    session = boto3.Session(profile_name=configs['profile'])
    client = session.client('s3')
    
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
