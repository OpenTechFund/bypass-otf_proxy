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
from log_reporting_utilities import analyze_file, output, report_save, filter_and_get_date

logger = logging.getLogger('logger')

@click.command()
@click.option('--percent', type=int, help="Floor percentage to display for agents and codes (default is 5%)", default=5)
@click.option('--num', type=int, help="Top number of pages to display (default is 10", default=10)
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
        domains_list.append({'id' : line[0], 'name' : line[1], 's3_bucket' : line[4]})


    for dm in domains_list:
        if ((domain == 'all') or (dm['name'] == domain)):
            try:
                s3simple = S3Simple(region_name=configs['region'],
                                            profile=configs['profile'],
                                            bucket_name=dm['s3_bucket'])
            except:
                logger.debug(f"No bucket set for domain {dm['name']}")
                continue

            # get the file list to analyze
            # read from S3
            logger.debug(f"Getting files from S3 bucket {dm['s3_bucket']}...")
            file_list = s3simple.s3_bucket_contents()
            if not file_list:
                continue
            logger.debug(f"File List: {file_list}")
            all_raw_data = ""
            for ifile in file_list:
                if 'LogAnalysis' in ifile:
                    continue
                if (('.gz' in ifile or '.bz2' in ifile) and not unzip):
                    continue
                logger.debug(f"Processing file: {ifile}")
                file_date = filter_and_get_date(ifile)
                if not file_date:
                    continue
                numdays = (now - file_date).days
                if numdays > range:
                    continue

                #download
                local_path = configs['local_tmp'] + '/' + ifile
                logger.debug(f"Downloading ... domain: {dm['name']} to {local_path}")
                s3simple.download_file(file_name=ifile, output_file=local_path)
                
                # Add to aggregate
                logger.debug(f"Adding to compilation... ")
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
                    with open(flocal_path) as f:
                        raw_data = f.read()

                logger.debug(f"Raw: {raw_data}")
                all_raw_data = all_raw_data + raw_data

            logger.debug(f"All data: {all_raw_data}")
            analyzed_data = analyze_file(all_raw_data, domain)
            if not analyzed_data:
                continue
            logger.debug(f"Visitor IPs:{analyzed_data['visitor_ips']}!")
            if analyzed_data['visitor_ips']:
                log_type = 'nginx'
            else:
                log_type = 'eotk'    
            logger.debug(f"Log type: {log_type}")
            (output_text, first_date, last_date, hits) = output(
                        domain=dm['name'],
                        data=analyzed_data,
                        percent=percent,
                        num=num)
            logger.debug(output_text)

            logger.debug("Saving log analysis file...")
            key = 'LogAnalysis_' + domain + '_' + now_string + '.json'
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