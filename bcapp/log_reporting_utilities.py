"""
Utilities for log reporting
Used by command line and flask app
"""
import re
import datetime
from simple_AWS.s3_functions import *
from proxy_utilities import get_configs

def analyze_file(raw_data):
    """
    Analyzes the raw data from the file - for status, agents and pages
    :arg: raw_data
    :returns: dict of dicts
    """
    raw_data_list = raw_data.split('\n')
    if len(raw_data_list) < 5: # Not worth analyzing
        return False
    analyzed_log_data = {
            'status': {},
            'user_agent': {},
            'pages_visited' : {}
        }
    analyzed_log_data['hits'] = len(raw_data_list)
    log_date_match = re.compile('[0-9]{2}[\/]{1}[A-Za-z]{3}[\/]{1}[0-9]{4}[:]{1}[0-9]{2}[:]{1}[0-9]{2}[:]{1}[0-9]{2}')
    log_status_match = re.compile('[\ ]{1}[0-9]{3}[\ ]{1}')
    datetimes = []
    for line in raw_data_list:
        log_data = {}
        try:
            log_data['datetime'] = log_date_match.search(line).group(0)
            log_data['status'] = log_status_match.search(line).group(0)
        except:
            continue
        datetimes.append(datetime.datetime.strptime(log_data['datetime'], '%d/%b/%Y:%H:%M:%S'))
        try:
            log_data['user_agent'] = line.split(' "')[-1]
        except:
            continue
        try:
            log_data['page_visited'] = line.split(' "')[-3].split(' ')[1]
        except:
            continue
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
        else:
            analyzed_log_data['pages_visited'][log_data['page_visited']] = 1

    datetimes.sort()
    analyzed_log_data['earliest_date'] = datetimes[0].strftime('%d/%b/%Y:%H:%M:%S')
    analyzed_log_data['latest_date'] = datetimes[-1].strftime('%d/%b/%Y:%H:%M:%S')

    return(analyzed_log_data)

def output(**kwargs):
    """
    Creates output
    """
    analyzed_log_data = kwargs['data']
    output = f"Analysis of: {kwargs['file_name']}, from {analyzed_log_data['earliest_date']} to {analyzed_log_data['latest_date']}:\n"
    output += f"Hits: {analyzed_log_data['hits']}\n"

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
    for (page, number) in ordered_pages_visited:
        perc = number/analyzed_log_data['hits'] * 100
        output += f"Page {page}: {perc:.1f}%\n"
        i += 1
        if i > kwargs['num']:
            break

    return output

def domain_log_reports(domain, report_type):
    """
    Setup for log reporting on a domain
    """
    configs = get_configs()
    # get filtered list
    file_list = get_file_list(
        region=configs['region'],
        profile=configs['profile'],
        bucket=configs['log_storage_bucket'],
        domain=domain
    )
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
        if ('output' in single_file) and (kwargs['domain'] in single_file):
            date_search = '[0-9]{2}[-][a-zA-Z]{3}-20[0-9]{2}:[0-9]{2}:[0-9]{2}:[0-9]{2}'
            match = re.search(date_search, single_file)
            date = datetime.datetime.strptime(match.group(0),'%d-%b-%Y:%H:%M:%S')
            filtered_list.append({'date': date, 'file_name': single_file})

    return filtered_list
    
    