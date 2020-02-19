"""
Analyze server stats for specific things related to onion services

version 0.2
"""
import sys
import os
import datetime
import configparser
import click
import sh
import re
import logging
from proxy_utilities import get_configs
from simple_AWS.s3_functions import *

@click.command()
@click.option('--percent', type=int, help="Floor percentage to display for agents and codes", default=0)
@click.option('--num', type=int, help="Top number of pages to display", default=10)
@click.option('--path', type=str, help="Path to find file/s - will use paths file by default")
@click.option('--recursive', is_flag=True, help="Descent through directories")
@click.option('--unzip', is_flag=True, help="Unzip and analyze zipped log files", default=False)
@click.option('--daemon', is_flag=True, default=False, help="Run in daemon mode. All output goes to a file.")
@click.option('--skipsave', is_flag=True, default=False, help="Skip saving log file to S3")

def analyze(path, recursive, unzip, percent, num, daemon, skipsave):
    configs = get_configs()
    paths = []
    now = datetime.datetime.now()
    now_string = now.strftime('%d-%b-%Y:%H:%M:%S')
    # get the file list to analyze
    if not path:
        # is there a path file?
        if configs['paths']:
            # open paths file
            with open(configs['paths']) as pathfile:
                raw_path_list = pathfile.read()
            path_list = raw_path_list.split('\n')
        paths = path_list
    else:
        paths.append(path)

    for fpath in paths:
        if not fpath:
            continue
        if not os.path.exists(fpath):
            logger.critical("Path doesn't exist!")
            return
        if not os.path.isdir(fpath):
            files = [path]
        else:
            files = get_list(fpath, recursive)

        all_log_data = []
        for file_name in files:
            if 'nginx-access' not in file_name:
                continue
            file_path = file_name.split('/')
            file_parts = file_path[-1].split('.')
            just_file_name = '.'.join(file_path)
            logger.debug(f"File Name {just_file_name}")
            ext = file_parts[-1]
            if ((ext != 'log') and
                (ext != 'bz2')): # not a log file, nor a zipped log file
                continue
            if ext == 'bz2':
                if unzip:
                    raw_data = sh.bunzip2("-k", "-c", file_name)
                else:
                    continue
            else:
                with open(file_name) as f:
                    raw_data = f.read()
            
            s3simple = S3Simple(region_name=configs['region'],
                                profile=configs['profile'],
                                bucket_name=configs['log_storage_bucket'])
            # send to S3
            if not skipsave:
                logger.debug("sending to s3...")
                s3_file =  'raw_log_file-' + just_file_name + now_string
                s3simple.send_file_to_s3(local_file=file_name, s3_file=s3_file)

            logger.debug("Analyzing...")
            analyzed_data = analyze_file(raw_data)
            output_text = output(
                        file_name=file_name,
                        data=analyzed_data,
                        percent=percent,
                        num=num)
            if not daemon:
                print(output_text)

            logger.debug("Saving log analysis file...")
            key = 'log_analysis' + just_file_name + '-' + now_string
            body = str(analyzed_data)
            s3simple.put_to_s3(key=key, body=body)

            logger.debug("Saving output file....")
            key = 'log_analysis_output' + just_file_name + '-' + now_string
            s3simple.put_to_s3(key=key, body=output_text)
    
    return
 
def analyze_file(raw_data):
    """
    Analyzes the raw data from the file - for status, agents and pages
    :arg: raw_data
    :returns: dict of dicts
    """
    raw_data_list = raw_data.split('\n')
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

def get_list(path, recursive):
    file_list = os.listdir(path)
    all_files = []
    for entry in file_list:
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path) and recursive:
            all_files = all_files + get_list(full_path, recursive)
        else:
            all_files.append(full_path)
    return all_files

if __name__ == '__main__':
    configs = get_configs()
    log = configs['log_level']
    logger = logging.getLogger('clogger')  # instantiate clogger
    logger.setLevel(logging.DEBUG)  # pass DEBUG and higher values to handler

    ch = logging.StreamHandler()  # use StreamHandler, which prints to stdout
    ch.setLevel(configs['log_level'])  # ch handler uses the configura

    # create formatter
    # display the function name and logging level in columnar format if
    # logging mode is 'DEBUG'
    formatter = logging.Formatter('[%(funcName)24s] [%(levelname)8s] %(message)s')

    # add formatter to ch
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    analyze()