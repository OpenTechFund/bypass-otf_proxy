"""
Analyze server stats for specific things related to onion services

version 0.1
"""
import sys
import os
import datetime
import configparser
import click
import sh
import re
from proxy_utilities import get_configs

@click.command()
@click.option('--percent', type=int, help="Floor percentage to display for agents and codes", default=0)
@click.option('--num', type=int, help="Top number of pages to display", default=10)
@click.option('--path', type=str, help="Path to find file/s - will use paths file by default")
@click.option('--recursive', is_flag=True, help="Descent through directories")
@click.option('--unzip', is_flag=True, help="Unzip and analyze zipped log files", default=False)
@click.option('--daemon', is_flag=True, default=False, help="Run in daemon mode. All output goes to a file.")

def analyze(path, recursive, unzip, percent, num, daemon):
    configs = get_configs()
    paths = []
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
            print("Path doesn't exist!")
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
            ext = file_parts[-1]
            if ((ext != 'log') and
                (ext != 'bz2')): # not a log file, nor a zipped log file
                continue
            if ext == 'bz2':
                if unzip:
                    raw_data = sh.bunzip2("-k", "-c", file_name)
                    # send to S3, delete from local
                else:
                    continue
            else:
                with open(file_name) as f:
                    raw_data = f.read()
            
            analyzed_data = analyze_file(raw_data)
            if not daemon:
                output(
                    file_name=file_name,
                    data=analyzed_data,
                    percent=percent,
                    num=num)

            # else: save json to a file, shunt to S3
 
def analyze_file(raw_data):
    """
    Analyzes the raw data from the file - for status, agents and pages
    :arg: raw_data
    :returns: dict of dicts
    """
    analyzed_log_data = {
            'status': {},
            'user_agent': {},
            'pages_visited' : {}
        }
    raw_data_list = raw_data.split('\n')
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
    Creates output if interactive
    """
    analyzed_log_data = kwargs['data']
    print(f"File: {kwargs['file_name']}, from {analyzed_log_data['earliest_date']} to {analyzed_log_data['latest_date']}:")
    print(f"Hits: {analyzed_log_data['hits']}\n")

    ordered_status_data = sorted(analyzed_log_data['status'].items(), 
                                    key=lambda kv: kv[1], reverse=True)
    print("Status Codes:")
    for (code, number) in ordered_status_data:
        perc = number/analyzed_log_data['hits'] * 100
        if perc >= kwargs['percent']:
            print(f"{code}: {perc:.1f}%")

    ordered_agent_data = sorted(analyzed_log_data['user_agent'].items(),
                                key=lambda kv: kv[1], reverse=True)
    print(f"Number of user agents: {len(ordered_agent_data)}")
    for (agent, number) in ordered_agent_data:
        perc = number/analyzed_log_data['hits'] * 100
        if perc >= kwargs['percent']:
            print(f"User agent {agent}: {perc:.1f}%")

    i = 0
    ordered_pages_visited = sorted(analyzed_log_data['pages_visited'].items(), key=lambda kv: kv[1], reverse=True)
    print(f"Number of pages visited: {len(ordered_pages_visited)}")
    print(f"Top {kwargs['num']} pages:")
    for (page, number) in ordered_pages_visited:
        perc = number/analyzed_log_data['hits'] * 100
        print(f"Page {page}: {perc:.1f}%")
        i += 1
        if i > kwargs['num']:
            break

    return

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
    analyze()