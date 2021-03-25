import sys
import os
import datetime
import time
import click
import sh
import logging
from dotenv import load_dotenv
import sqlalchemy as db
from system_utilities import get_configs
from simple_AWS.s3_functions import *

logger = logging.getLogger('logger')

@click.command()
@click.option('--daemon', is_flag=True, default=False, help="Run in daemon mode. All output goes to a file.")
@click.option('--zip', is_flag=True, help="Save zipped log files", default=False)
@click.option('--recursive', is_flag=True, help="Descent through directories")
@click.option('--range', type=int, help="Days of log file age to save. Default is 7", default=7)

def move_logs(daemon, zip, recursive, range):
    """
    Move logs from local to s3
    """
    configs = get_configs()
    now = datetime.datetime.now()
    now_string = now.strftime('%d-%b-%Y:%H:%M:%S')
    
    logger.debug("Reading Local Files...")
    if configs['paths']:
        # open paths file
        with open(configs['paths']) as pathfile:
            raw_path_list = pathfile.read()
        paths = raw_path_list.split('\n')

    for fpath in paths:
        if not fpath:
            continue
        domain, path = fpath.split('|')

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

        domain_match = False
        for db_domain in domains_list:
            if ((db_domain['name'] == domain) and (db_domain['s3_bucket'])):
                domain_match = True
                s3simple = S3Simple(region_name=configs['region'],
                                profile=configs['profile'],
                                bucket_name=db_domain['s3_bucket'])

        if not domain_match:
            logger_debug("No s3 bucket match!")
            continue

        if not os.path.exists(path):
            logger.critical("Path doesn't exist!")
            return
        if not os.path.isdir(path):
            files = [path]
        else:
            files = get_list(path, recursive, range)

        logger.debug(f"Path: {path}")

        # send to S3
        for file_name in files:
            if 'access' not in file_name:
                    continue
            file_path = file_name.split('/')
            file_parts = file_path[-1].split('.')
            just_file_name = '.'.join(file_path)
            logger.debug(f"File Name {just_file_name}")
            ext = file_parts[-1]
            if ((ext == 'bz2' or ext == 'gz')) and not zip:
                continue 
            logger.debug("sending to s3...")
            s3_file =  'RawLogFile_' + domain + '_' + now_string + '_' + just_file_name
            s3simple.send_file_to_s3(local_file=file_name, s3_file=s3_file)

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

    move_logs()
