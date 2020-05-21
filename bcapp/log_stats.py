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
from proxy_utilities import get_configs
from simple_AWS.s3_functions import *
from log_reporting_utilities import analyze_file, output, report_save

logger = logging.getLogger('logger')

@click.command()
@click.option('--percent', type=int, help="Floor percentage to display for agents and codes (default is 5%)", default=5)
@click.option('--num', type=int, help="Top number of pages to display (default is 10", default=10)
@click.option('--recursive', is_flag=True, help="Descent through directories")
@click.option('--unzip', is_flag=True, help="Unzip and analyze zipped log files", default=False)
@click.option('--daemon', is_flag=True, default=False, help="Run in daemon mode. All output goes to a file.")
@click.option('--skipsave', is_flag=True, default=False, help="Skip saving log file to S3")
@click.option('--paths_ignore', type=str, help="Comma delimited list (no spaces) of paths to ignore for log analysis.")
@click.option('--justsave', is_flag=True, default=False, help="Just save log files to S3, don't run any analysis.")
@click.option('--read_s3', is_flag=True, default=False, help="Read logfiles from S3, not from local paths.")
@click.option('--range', type=int, help="Days of log file age to analyze. Default is 10", default=10)

def analyze(recursive, unzip, percent, num, daemon, skipsave, paths_ignore, justsave, read_s3, range):

    import faulthandler; faulthandler.enable()
    
    configs = get_configs()
    now = datetime.datetime.now()
    now_string = now.strftime('%d-%b-%Y:%H:%M:%S')

    s3simple = S3Simple(region_name=configs['region'],
                                profile=configs['profile'],
                                bucket_name=configs['log_storage_bucket'])

    # get the file list to analyze
    if not read_s3:
        logger.debug("Reading Local Files...")
        if configs['paths']:
            # open paths file
            with open(configs['paths']) as pathfile:
                raw_path_list = pathfile.read()
            paths = raw_path_list.split('\n')
    else: # read from S3, and download to local tmp
        logger.debug("Getting files from S3 bucket...")
        file_list = s3simple.s3_bucket_contents()
        logger.debug(f"File list: {file_list}")
        paths = []
        for ifile in file_list:
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
            # Download to tmp
            local_path = configs['local_tmp'] + '/' + ifile
            paths.append(f"{domain}|{local_path}")
            logger.debug(f"Downloading ... domain: {domain} to {local_path}")
            s3simple.download_file(file_name=ifile, output_file=local_path)

    logger.debug(f"Paths: {paths}")

    for fpath in paths:
        if not fpath:
            continue
        logger.debug(f"Path: {fpath}")
        domain, path = fpath.split('|')
        if not os.path.exists(path):
            logger.critical("Path doesn't exist!")
            return
        if not os.path.isdir(path):
            files = [path]
        else:
            files = get_list(path, recursive, range)

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
            
            # send to S3
            if not skipsave and not read_s3:
                logger.debug("sending to s3...")
                s3_file =  'RawLogFile_' + domain + '_' + now_string + '_' + just_file_name
                s3simple.send_file_to_s3(local_file=file_name, s3_file=s3_file)

            if not justsave:
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

                analyzed_data = analyze_file(raw_data, paths_ignore)
                if not analyzed_data:
                    continue
                (output_text, first_date, last_date, hits) = output(
                            file_name=file_name,
                            data=analyzed_data,
                            percent=percent,
                            num=num)
                if not daemon:
                    print(output_text)

                logger.debug("Saving log analysis file...")
                key = 'LogAnalysis_' + just_file_name + '_' + now_string + '.json'
                body = str(analyzed_data)
                s3simple.put_to_s3(key=key, body=body)

                logger.debug("Saving output file....")
                key = 'LogAnalysisOutput_' + domain + '_' + now_string + '.txt'
                s3simple.put_to_s3(key=key, body=output_text)
    
                logger.debug("Sending Report to Database...")
                report_save(
                    domain=domain,
                    datetime=now,
                    report_text=output_text,
                    hits=hits,
                    first_date_of_log=first_date,
                    last_date_of_log=last_date,
                    )

    return

def get_list(path, recursive, range):
    now = datetime.datetime.now()
    file_list = os.listdir(path)
    all_files = []
    for entry in file_list:
        full_path = os.path.join(path, entry)
        # How old is the file?
        modified = datetime.datetime.fromtimestamp(os.path.getmtime(full_path))
        numdays = (now - modified).days
        logger.debug(f"File: {full_path} Age: {numdays}")
        if numdays > range:
            continue
        if os.path.isdir(full_path) and recursive:
            all_files = all_files + get_list(full_path, recursive)
        else:
            all_files.append(full_path)
    return all_files

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