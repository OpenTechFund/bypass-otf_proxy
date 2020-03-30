"""
Analyze server stats for specific things related to onion services

version 0.2
"""
import sys
import os
import datetime
import click
import sh
import logging
from proxy_utilities import get_configs
from simple_AWS.s3_functions import *
from log_reporting_utilities import analyze_file, output

@click.command()
@click.option('--percent', type=int, help="Floor percentage to display for agents and codes (default is 5%)", default=5)
@click.option('--num', type=int, help="Top number of pages to display (default is 10", default=10)
@click.option('--recursive', is_flag=True, help="Descent through directories")
@click.option('--unzip', is_flag=True, help="Unzip and analyze zipped log files", default=False)
@click.option('--daemon', is_flag=True, default=False, help="Run in daemon mode. All output goes to a file.")
@click.option('--skipsave', is_flag=True, default=False, help="Skip saving log file to S3")
@click.option('--paths_ignore', type=str, help="Comma delimited list (no spaces) of paths to ignore for log analysis.")

def analyze(recursive, unzip, percent, num, daemon, skipsave, paths_ignore):
    configs = get_configs()
    now = datetime.datetime.now()
    now_string = now.strftime('%d-%b-%Y:%H:%M:%S')
    # get the file list to analyze
    if configs['paths']:
        # open paths file
        with open(configs['paths']) as pathfile:
            raw_path_list = pathfile.read()
        paths = raw_path_list.split('\n')

    for fpath in paths:
        if not fpath:
            continue
        domain, path = fpath.split(':')
        if not os.path.exists(path):
            logger.critical("Path doesn't exist!")
            return
        if not os.path.isdir(path):
            files = [path]
        else:
            files = get_list(path, recursive)

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
            analyzed_data = analyze_file(raw_data, paths_ignore)
            if not analyzed_data:
                continue
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
            key = 'log_analysis_output-' + domain + '-' + now_string
            s3simple.put_to_s3(key=key, body=output_text)
    
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