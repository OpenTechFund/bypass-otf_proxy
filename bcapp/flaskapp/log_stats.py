"""
Analyze server stats for specific things related to onion services

version 0.2
"""
import sys
import os
import datetime
import time
import click
import sh
import logging
from system_utilities import get_configs
from simple_AWS.s3_functions import *
from log_reporting_utilities import analyze_file, output, report_save

logger = logging.getLogger('logger')

@click.command()
@click.option('--percent', type=int, help="Floor percentage to display for agents and codes (default is 5%)", default=5)
@click.option('--num', type=int, help="Top number of pages to display (default is 10", default=10)
@click.option('--unzip', is_flag=True, help="Process zipped log files", default=False)
@click.option('--daemon', is_flag=True, default=False, help="Run in daemon mode. All output goes to a file.")
@click.option('--range', type=int, help="Days of log file age to analyze. Default is 7", default=7)

def analyze(unzip, percent, num, daemon, range):

    import faulthandler; faulthandler.enable()

    configs = get_configs()
    now = datetime.datetime.now()
    now_string = now.strftime('%d-%b-%Y:%H:%M:%S')

    # TODO: Make this domain specific
    s3simple = S3Simple(region_name=configs['region'],
                                profile=configs['profile'],
                                bucket_name=configs['log_storage_bucket'])

    # get the file list to analyze
    # read from S3
    logger.debug("Getting files from S3 bucket...")
    file_list = s3simple.s3_bucket_contents()
    logger.debug(f"File list: {file_list}")
    paths = []
    for ifile in file_list:
        if (('.gz' in ifile or '.bz2' in ifile) and not unzip):
            continue
        logger.debug(f"Processing file: {ifile}")
        try:
            (prefix, domain, date, filename) = ifile.split('_')
        except ValueError:
            continue
        if prefix != 'RawLogFile':
            continue
        file_date = datetime.datetime.strptime(date, "%d-%b-%Y:%H:%M:%S")
        numdays = (now - file_date).days
        if numdays > range:
            continue
        paths.append(f"{domain}|{ifile}")

    logger.debug(f"Paths: {paths}")

    for fpath in paths:
        if not fpath:
            continue
        domain, path = fpath.split('|')
        
        #download
        local_path = configs['local_tmp'] + '/' + path
        logger.debug(f"Downloading ... domain: {domain} to {local_path}")
        s3simple.download_file(file_name=path, output_file=local_path)
        files = [local_path]

        logger.debug(f"File List: {files}")

        all_log_data = []
        for file_name in files:
            if 'access' not in file_name:
                continue
            file_path = file_name.split('/')
            file_parts = file_path[-1].split('.')
            just_file_name = '.'.join(file_path)
            logger.debug(f"File Name {just_file_name}")
            ext = file_parts[-1]
            if ((ext != 'log') and
                (ext != 'bz2' and ext !='gz')): # not a log file, nor a zipped log file
                continue

            logger.debug(f"Analyzing... ")
            if ext == 'bz2' or ext == 'gz':
                if unzip:
                    if ext == 'bz2':
                        raw_data = sh.bunzip2("-k", "-c", file_name)
                    else:
                        raw_data = sh.gunzip("-k", "-c", file_name)
                else:
                    continue
            else:
                with open(file_name) as f:
                    raw_data = f.read()

            analyzed_data = analyze_file(raw_data, domain)
            logger.debug(f"Visitor IPs:{analyzed_data['visitor_ips']}!")
            if analyzed_data['visitor_ips']:
                log_type = 'nginx'
            else:
                log_type = 'eotk'    
            if not analyzed_data:
                continue
            logger.debug(f"Log type: {log_type}")
            (output_text, first_date, last_date, hits) = output(
                        file_name=file_name,
                        data=analyzed_data,
                        percent=percent,
                        num=num)
            logger.debug(output_text)

            logger.debug("Saving log analysis file...")
            key = 'LogAnalysis_' + just_file_name + '_' + now_string + '.json'
            body = str(analyzed_data)
            s3simple.put_to_s3(key=key, body=body)

            logger.debug("Saving output file....")
            key = 'LogAnalysisOutput_' + domain + '_' + log_type + '_' + now_string + '.txt'
            s3simple.put_to_s3(key=key, body=output_text)

            logger.debug(f"Deleting local temporary file {local_path}...")
            os.remove(local_path)

            logger.debug("Sending Report to Database...")
            report_save(
                domain=domain,
                datetime=now,
                report_text=output_text,
                hits=hits,
                first_date_of_log=first_date,
                last_date_of_log=last_date,
                log_type=log_type
                )

    return

if __name__ == '__main__':
    configs = get_configs()
    log = configs['log_level']
    logger = logging.getLogger('logger')  # instantiate clogger
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