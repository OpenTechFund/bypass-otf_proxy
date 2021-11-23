"""
Utilities for log reporting
Used by command line and flask app
"""
import re
import os
import datetime
import logging
import json
from dotenv import load_dotenv
from simple_AWS.s3_functions import *
import sqlalchemy as db
from system_utilities import get_configs
from db_utilities import get_domain_data, report_save

logger = logging.getLogger('logger')

def analyze_file(raw_data, domain):
    """
    Analyzes the raw data from the file - for status, agents and pages
    :arg: raw_data
    :returns: dict of dicts
    """
    domain_data = get_domain_data(domain)
    if not domain_data:
        return False

    if domain_data['paths_ignore']:
        paths_ignore_list = domain_data['paths_ignore'].split(',')
    else:
        paths_ignore_list = False
    if domain_data['ext_ignore']:
        exts_ignore_list = domain_data['ext_ignore'].split(',')
    else:
        exts_ignore_list = False
    
    #logger.debug(f"Paths: {paths_ignore_list} Ext: {exts_ignore_list}")

    raw_data_list = raw_data.split('\n')
    #logger.debug(f"raw length: {len(raw_data_list)} first chars: {raw_data_list[0][0]}")
    fastly_log_match = re.compile('\<\d{3}\>')
    try:
        fastly_match = fastly_log_match.search(raw_data_list[0]).group(0)
    except:
        fastly_match = False
    #What kind of log formats are these?
    if raw_data_list[0][0] == '{': # it's json
        log_type = 'azure'
    elif 'Version' in raw_data_list[0]: #cloudfront
        log_type = 'cloudfront'
        raw_data_list = raw_data_list[2:] #getting rid of first two lines, which are comments
    elif fastly_match: # Fastly logs have '<###>' at the beginning of each line
        log_type = 'fastly'
    else:
        log_type = 'nginx'

    logger.debug(F"Log type: {log_type}")
    final_log_data = []
    for line in raw_data_list:
        if not line:
            continue
        if line[0] == '#':
            continue
        log_data = {}
        if log_type == 'nginx':
            log_date_match = re.compile('[0-9]{2}[\/]{1}[A-Za-z]{3}[\/]{1}[0-9]{4}[:]{1}[0-9]{2}[:]{1}[0-9]{2}[:]{1}[0-9]{2}')
            log_status_match = re.compile('[\ ]{1}[0-9]{3}[\ ]{1}')
            log_ip_match = re.compile('[0-9]{1,3}[\.]{1}[0-9]{1,3}[\.]{1}[0-9]{1,3}[\.]{1}[0-9]{1,3}')
            try:
                log_data['datetime'] = log_date_match.search(line).group(0)
                log_data['status'] = log_status_match.search(line).group(0)
                log_data['ip'] = log_ip_match.search(line).group(0)
            except:
                pass
            try:
                log_data['user_agent'] = line.split(' "')[-1]
            except:
                pass
            try:
                log_data['page_visited'] = line.split(' "')[-3].split(' ')[1]
            except:
                pass
        elif log_type == 'cloudfront':
            line_items = line.split('\t')
            try:
                ymd = line_items[0]
                hms = line_items[1]
                date_time = ymd + '\t' + hms
                log_data['datetime'] = date_time
                log_data['status'] = line_items[8]
                log_data['user_agent'] = line_items[10]
                log_data['page_visited'] = line_items[7]
            except:
                continue
        elif log_type == 'fastly':
            line_items = line.split(' ')
            # We will parse assuming format: %v %h %t %m "%r" %>s
            try:
                log_data['status'] = line_items[11]
                log_data['datetime'] = line_items[5]
                log_data['user_agent'] = 'No User Agent Recorded'
                log_data['page_visited'] = line_items[9]
                log_data['ip'] = line_items[4]
                log_domain = line_items[3]
            except:
                continue
            if ((len(log_data['status']) != 3) or ('.' not in log_data['ip']) or (log_data['datetime'][0] != '[')):
                # log format is off
                continue
            
        elif log_type == 'azure':
            try:
                line_json = json.loads(line)
            except:
                logger.debug("Can't parse - isn't json!")
                continue

            log_data['status'] = line_json['properties']['httpStatusCode']
            log_data['datetime'] = line_json['time']
            log_data['user_agent'] = line_json['properties']['userAgent']
            log_data['page_visited'] = line_json['properties']['requestUri']
            log_data['ip'] = line_json['properties']['clientIp']

        else:
            continue

        if 'page_visited' not in log_data:
            continue
            
        if exts_ignore_list:
            ext_ignore = False
            for ext in exts_ignore_list:
                if ext in log_data['page_visited']:
                    ext_ignore = True
            if ext_ignore:
                #logger.debug(f"page: {log_data['page_visited']} Ignore: {ext_ignore} ")
                continue
        if paths_ignore_list:
            should_skip = False
            for ignore in paths_ignore_list:
                ig_len = len(ignore)
                if ignore == log_data['page_visited'][:ig_len]:
                    should_skip = True
            if should_skip:
                #logger.debug(f"page: {log_data['page_visited'][:ig_len]} - Skip: {should_skip}")
                continue
        
        final_log_data.append(log_data)
        
    return final_log_data, log_type

def analyze_data(compiled_log_data, log_type):
    """
    Analyze compiled data from different logs
    """
    # logger.debug(f"Compiled data: {compiled_log_data}")

    analyzed_log_data = {
            'visitor_ips': {},
            'status': {},
            'user_agent': {},
            'pages_visited' : {}
        }
    analyzed_log_data['hits'] = len(compiled_log_data)

    datetimes = []
    for log_data in compiled_log_data:
        if log_type == 'nginx':
            try:
                log_date = datetime.datetime.strptime(log_data['datetime'], '%d/%b/%Y:%H:%M:%S')
            except:
                log_date = False
        elif log_type == 'fastly':
            try:
                log_date = datetime.datetime.strptime(log_data['datetime'], '[%d/%b/%Y:%H:%M:%S')
            except:
                log_date = False
        elif log_type == 'cloudfront':
            try:
                log_date = datetime.datetime.strptime(log_data['datetime'], '%Y-%m-%d\t%H:%M:%S')
            except:
                log_date = False
        elif log_type == 'azure':
            try:
                log_date = datetime.datetime.strptime(log_data['datetime'][:-2], '%Y-%m-%dT%H:%M:%S.%f')
            except:
                log_date = False

        if log_date:
            datetimes.append(log_date)
        else:
            continue
        
        if 'ip' in log_data:
            if log_data['ip'] in analyzed_log_data['visitor_ips']:
                analyzed_log_data['visitor_ips'][log_data['ip']] += 1
            else:
                analyzed_log_data['visitor_ips'][log_data['ip']] = 1
        if log_data['status'] in analyzed_log_data['status']:
            analyzed_log_data['status'][log_data['status']] += 1
        else:
            analyzed_log_data['status'][log_data['status']] = 1
        if log_data['user_agent'] in analyzed_log_data['user_agent']:
            analyzed_log_data['user_agent'][log_data['user_agent']] += 1
        else:
            analyzed_log_data['user_agent'][log_data['user_agent']] = 1

        if log_data['page_visited'] in analyzed_log_data['pages_visited']:
            analyzed_log_data['pages_visited'][log_data['page_visited']] += 1
            if log_type != 'azure':
                if ((log_data['page_visited'] == '/') or
                    (re.compile("\:[0-9]{2,3}\/$").search(log_data['page_visited']))): #home page
                    analyzed_log_data['home_page_hits'] += 1
        else:
            analyzed_log_data['pages_visited'][log_data['page_visited']] = 1
            if ((log_data['page_visited'] == '/') or
                (re.compile("\:[0-9]{2,3}\/$").search(log_data['page_visited']))): #home page
                analyzed_log_data['home_page_hits'] = 1

    datetimes.sort()
    if datetimes:
        analyzed_log_data['earliest_date'] = datetimes[0].strftime('%d/%b/%Y:%H:%M:%S')
        analyzed_log_data['latest_date'] = datetimes[-1].strftime('%d/%b/%Y:%H:%M:%S')

    return(analyzed_log_data)

def output(**kwargs):
    """
    Creates output
    """
    analyzed_log_data = kwargs['data']
    if 'home_page_hits' in analyzed_log_data:
        home_page_hits = analyzed_log_data['home_page_hits']
    else:
        home_page_hits = 1
    if 'hits' in analyzed_log_data:
        hits = analyzed_log_data['hits']
    else:
       return False
    
    if ('earliest_date' in analyzed_log_data) and ('latest_date' in analyzed_log_data):
        first_date = analyzed_log_data['earliest_date']
        last_date = analyzed_log_data['latest_date']
    else:
        first_date = False
        last_date = False

    output = f"Analysis of: {kwargs['domain']}, from {first_date} to {last_date}:\n"
    output += f"Hits: {hits}\n"

    if 'visitor_ips' in analyzed_log_data:
        #logger.debug(f"Visitor IPs in data: {analyzed_log_data['visitor_ips']}")
        output += f"IP addresses: \n"
        for data in analyzed_log_data['visitor_ips']:
            perc = analyzed_log_data['visitor_ips'][data]/analyzed_log_data['hits'] * 100
            if perc >= kwargs['percent']:
                output += f"{data}: {perc:.1f}%\n"

    ordered_status_data = sorted(analyzed_log_data['status'].items(), 
                                    key=lambda kv: kv[1], reverse=True)
    output += "Status Codes:\n"
    for (code, number) in ordered_status_data:
        perc = number/analyzed_log_data['hits'] * 100
        if perc >= kwargs['percent']:
            output += f"{code}: {perc:.1f}%\n"

    ordered_agent_data = sorted(analyzed_log_data['user_agent'].items(),
                                key=lambda kv: kv[1], reverse=True)
    output += f"Number of user agents: {len(ordered_agent_data)}\n"
    for (agent, number) in ordered_agent_data:
        perc = number/analyzed_log_data['hits'] * 100
        if perc >= kwargs['percent']:
            output += f"User agent {agent}: {perc:.1f}%\n"

    i = 0
    ordered_pages_visited = sorted(analyzed_log_data['pages_visited'].items(), key=lambda kv: kv[1], reverse=True)
    output += f"Number of pages visited: {len(ordered_pages_visited)}\n"
    output += f"Top {kwargs['num']} pages:\n"
    output += f"Home Page Hits: {home_page_hits}\n"
    for (page, number) in ordered_pages_visited:
        perc = number/analyzed_log_data['hits'] * 100
        output += f"Page {page}: {number} {perc:.1f}%\n"
        i += 1
        if i > kwargs['num']:
            break

    return (output, first_date, last_date, hits, home_page_hits)

def domain_log_reports(domain, report_type):
    """
    Reports of log reports
    """
    configs = get_configs()
    # get filtered list
    file_list = get_file_list(
        region=configs['region'],
        profile=configs['profile'],
        bucket=configs['log_storage_bucket'],
        domain=domain,
        filter='Output'
    )

    if not file_list:
        return False

    # Sort by date
    sorted_list = sorted(file_list, key=lambda i: i['date'], reverse=True)

    if report_type == 'latest':
        output_contents = get_output_contents(
            bucket=configs['log_storage_bucket'],
            profile=configs['profile'],
            region=configs['region'],
            output_file=sorted_list[0]['file_name'],
            local_tmp=configs['local_tmp'])
        return output_contents

def filter_and_get_date(filename):
    """
    Get date of filename, and make sure it's a file to analyze
    """
    # Discern Date Format
    # Cloudfront file name format: DistributionID.%Y-%m-%d-%H.Some_weird_id.gz
    cloudmatch = "[\d]{4}\-[0,1][\d]\-[\d]{2}\-[\d]{2}"
    cfdate = re.search(cloudmatch, filename)
    nginx_match = "[\d]{2}\-[A-Z]{1}[a-z]{2}\-[\d]{4}\:[\d]{2}\:[\d]{2}\:[\d]{2}"
    ngdate = re.search(nginx_match, filename)
    fastly_match = "\d{4}-\d{2}-\d{2}T\d{2}\:\d{2}\:\d{2}"
    fastly_date = re.search(fastly_match, filename)
    azure_match = "\_[0-9]{4}\-[0-9]{2}\-[0-9]{2}\-[0-9]{2}\-[0-9]{2}\.json"
    azure_date = re.search(azure_match, filename)
    if cfdate:
        date = cfdate.group(0)
        file_date = datetime.datetime.strptime(date, "%Y-%m-%d-%H")
    elif ngdate:
        date = ngdate.group(0)
        file_date = datetime.datetime.strptime(date, "%d-%b-%Y:%H:%M:%S")
    elif fastly_date:
        date = fastly_date.group(0)
        file_date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
    elif azure_date:
        date = azure_date.group(0)
        file_date = datetime.datetime.strptime(date, "_%Y-%m-%d-%H-%M")
    else:
        file_date = False
    return file_date

def domain_log_list(domain, num):
    """
    List of domain logs
    """
    configs = get_configs()
    # get filtered list
    file_list = get_file_list(
        region=configs['region'],
        profile=configs['profile'],
        bucket=configs['log_storage_bucket'],
        domain=domain,
        filter='Raw'
    )

    if not file_list:
        return False

    sorted_list = sorted(file_list, key=lambda i: i['date'], reverse=True)

    return sorted_list[0:num]

def get_output_contents(**kwargs):
    """
    Gets the contents of specific output file
    """
    s3simple = S3Simple(region_name=kwargs['region'],
                        bucket_name=kwargs['bucket'],
                        profile=kwargs['profile'])
    local_file_name = kwargs['local_tmp'] + '/' + kwargs['output_file']
    s3simple.download_file(file_name=kwargs['output_file'], output_file=local_file_name)

    with open(local_file_name) as f:
        output = f.read()

    return output

def get_file_list(**kwargs):
    """
    Get the right list of files, keyed by date
    """
    s3simple = S3Simple(region_name=kwargs['region'],
                        bucket_name=kwargs['bucket'],
                        profile=kwargs['profile'])
    file_list = s3simple.s3_bucket_contents()
    filtered_list = []
    for single_file in file_list:
        if (kwargs['filter'] in single_file) and (kwargs['domain'] in single_file):
            date_search = '[0-9]{2}[-][a-zA-Z]{3}-20[0-9]{2}:[0-9]{2}:[0-9]{2}:[0-9]{2}'
            match = re.search(date_search, single_file)
            date = datetime.datetime.strptime(match.group(0),'%d-%b-%Y:%H:%M:%S')
            filtered_list.append({'date': date, 'file_name': single_file})

    return filtered_list

