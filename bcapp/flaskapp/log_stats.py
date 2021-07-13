"""
Analyze server stats for specific things related to onion services

version 0.2
"""
import sys
import os
import re
import datetime
import time
import click
import sh
import logging
from dotenv import load_dotenv
import sqlalchemy as db
from system_utilities import get_configs
from simple_AWS.s3_functions import *
from log_reporting_utilities import analyze_file, analyze_data, output, filter_and_get_date
from db_utilities import report_save
from azure_utilities import retrieve_logs

logger = logging.getLogger('logger')

@click.command()
@click.option('--percent', type=int, help="Floor percentage to display for agents and codes (default is 1%)", default=1)
@click.option('--num', type=int, help="Top number of pages to display (default is 30", default=30)
@click.option('--unzip', is_flag=True, help="Process zipped log files", default=False)
@click.option('--daemon', is_flag=True, default=False, help="Run in daemon mode. All output goes to a file.")
@click.option('--range', type=int, help="Days of log file age to analyze. Default is 7", default=7)
@click.option('--domain', type=str, help="Domain to analyze. Default is 'all'", default='all')

def analyze(unzip, percent, num, daemon, range, domain):

    import faulthandler; faulthandler.enable()

    configs = get_configs()
    now = datetime.datetime.now()
    now_string = now.strftime('%d-%b-%Y:%H:%M:%S')

    load_dotenv()
    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    domains = db.Table('domains', metadata, autoload=True, autoload_with=engine)
    domains_list = []
    query = db.select([domains])
    result = connection.execute(query).fetchall()
    for line in result:
        domains_list.append({'id' : line[0], 'name' : line[1], 's3_bucket' : line[4], 'azure_profile' : line[5]})


    for dm in domains_list:
        if ((domain == 'all') or (dm['name'] == domain)):
            # First, is there an azure profile set?
            if ('azure_profile' in dm) and (dm['azure_profile']):
                logger.debug(f"Domain: {dm['name']}: Azure Profile: {dm['azure_profile']}")
                retrieve_logs(profile_name=dm['azure_profile'], range=range, s3_bucket=dm['s3_bucket'])

            try:
                s3simple = S3Simple(region_name=configs['region'],
                                            profile=configs['profile'],
                                            bucket_name=dm['s3_bucket'])
            except:
                logger.warning(f"No bucket set for domain {dm['name']}")
                continue

            # get the file list to analyze
            # read from S3
            #logger.debug(f"Getting files from S3 bucket {dm['s3_bucket']}...")
            file_list = s3simple.s3_bucket_contents()
            if not file_list:
                continue
            logger.debug(f"File List: {file_list}")
            compiled_data = {
                'nginx': [],
                'cloudfront': [],
                'fastly': [],
                'azure': []
            }
            logger.debug(f"Analyzing {dm['name']}...")
            for ifile in file_list:
                if 'LogAnalysis' in ifile:
                    continue
                if (('.gz' in ifile or '.bz2' in ifile) and not unzip):
                    continue
                logger.debug(f"Processing file: {ifile}")
                if ifile[-1] == '/':
                    directory = configs['local_tmp'] + '/' + ifile
                    if not os.path.isdir(directory):
                        os.mkdir(directory)
                    continue
                file_date = filter_and_get_date(ifile)
                if not file_date:
                    logger.warning("Couldn't find date in logs!")
                    continue
                numdays = (now - file_date).days
                if numdays > range:
                    continue

                #download
                local_path = configs['local_tmp'] + '/' + ifile
                #logger.debug(f"Downloading ... domain: {dm['name']} to {local_path}")
                try:
                    s3simple.download_file(file_name=ifile, output_file=local_path)
                except:
                    continue
                
                # Add to aggregate
                file_parts = ifile.split('.')
                ext = file_parts[-1]
                if ext == 'bz2' or ext == 'gz':
                    if unzip:
                        if ext == 'bz2':
                            raw_data = str(sh.bunzip2("-k", "-c", local_path))
                        else:
                            raw_data = str(sh.gunzip("-k", "-c", local_path))
                    else:
                        continue
                else:
                    with open(local_path) as f:
                        raw_data = f.read()

                #logger.debug(f"Files data: {raw_data}")
                compiled_log_data, log_type = analyze_file(raw_data, dm['name'])
                if not compiled_log_data:
                    logger.warning("No Data!")
                    continue
                
                compiled_data[log_type] += compiled_log_data

                #logger.debug(f"Deleting local temporary file {local_path}...")
                os.remove(local_path)

            for log_type in compiled_data:
                logger.debug(f"Log type: {log_type}")
                #logger.debug(f"Analyzed data: {compiled_data[log_type]}")
                if not compiled_data[log_type]:
                    continue
                analyzed_log_data = analyze_data(compiled_data[log_type], log_type)
                (output_text, first_date, last_date, hits, home_page_hits) = output(
                            domain=dm['name'],
                            data=analyzed_log_data,
                            percent=percent,
                            num=num)
                logger.debug(output_text)

                logger.debug("Saving log analysis file...")
                key = 'LogAnalysis_'  + dm['name'] + '_' + log_type + '_' + now_string + '.json'
                body = str(analyzed_log_data)
                s3simple.put_to_s3(key=key, body=body)

                logger.debug("Saving output file....")
                key = 'LogAnalysisOutput_' + dm['name'] + '_' + log_type + '_' + now_string + '.txt'
                s3simple.put_to_s3(key=key, body=output_text)

                logger.debug("Sending Report to Database...")
                report_save(
                    domain=dm['name'],
                    datetime=now,
                    report_text=output_text,
                    hits=hits,
                    home_page_hits=home_page_hits,
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