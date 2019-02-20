"""
Mirror functions

Usage: mirror.py [-h] [--config=PATH_TO_CONFIG] [--clog=LEVEL]...

Options:
 -h --help
 --config=CONFIG  configuraton file
 --clog=LEVEL logging level
"""
import datetime
import time
import os
import logging
import pywebcopy
from pywebcopy import save_website
from pywebcopy import config
import configparser
from docopt import docopt

DEFAULT_CONFIG = 'mirror.cfg'

if __name__ == '__main__':
    ARGUMENTS = docopt(__doc__)
    CONFIG_FILE = ARGUMENTS['--config']
    if not ARGUMENTS['--clog']:
        clog = 'INFO'
    else:
        clog = ARGUMENTS['--clog'][0].upper()
    if not CONFIG_FILE:
        CONFIG_FILE = DEFAULT_CONFIG
    mirror_config = configparser.ConfigParser()
    try:
        mirror_config.read(CONFIG_FILE)
    except (IOError, OSError):
        print('Config File not found or not readable!')
        quit()

    logger = logging.getLogger('clogger')  # instantiate clogger
    logger.setLevel(logging.DEBUG)  # pass DEBUG and higher values to handler

    # create console handler and set its threshold to the command line argument
    ch = logging.StreamHandler()  # use StreamHandler, which prints to stdout
    ch.setLevel(clog)  # ch handler uses clog as threshold, which is CLI arg

    # create formatter
    # display the function name and logging level in columnar format if
    # logging mode is 'DEBUG'
    if clog == 'DEBUG' or clog == 'INFO':
        formatter = logging.Formatter('%(processName)11s [%(funcName)24s] [%('
                                        'levelname)8s] %(message)s')
    # otherwise, display a simplified log
    else:
        formatter = logging.Formatter('%(message)s (%(levelname)s)')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)

    # Set up configurations for pywebcopy

    url = mirror_config.get('MIRROR', 'site_to_mirror')
    local_files = mirror_config.get('MIRROR', 'local_files')
    parser = mirror_config.get('MIRROR', 'copy_parser')
    name = mirror_config.get('MIRROR', 'project_name')

    if mirror_config.get('MIRROR', 'copy_debug') == 'True':
        copy_debug = True
    else:
        copy_debug = False

    if mirror_config.get('MIRROR', 'copy_overwrite') == 'True':
        copy_overwrite = True
    else:
        copy_overwrite = False

    pywebcopy.config.setup_config(url, local_files, name)
    pywebcopy.config['ALLOWED_FILE_EXT'] = [
        '.html', '.css', '.json', '.js',
        '.xml','.svg', '.gif', '.ico',
        '.jpeg', '.jpg', '.png', '.ttf',
        '.eot', '.otf', '.woff', '', '.b', '.pwcf']
    pywebcopy.config['DEBUG'] = copy_debug

    logger.info("Starting Crawl...")
    
    save_website(
        url=url,
        project_folder=local_files,
)

exit()