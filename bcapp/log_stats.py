"""
Analyze server stats for specific things related to onion services

version 0.1
"""
import sys
import os
import configparser
import click
import sh
from proxy_utilities import get_configs

@click.command()
@click.option('--codes', is_flag=True, help="Status code frequency")
@click.option('--agents', is_flag=True, help="Frequency of user agents")
@click.option('--genstats', is_flag=True, help="General stats for log files")
@click.option('--path', type=str, help="Path to find file/s", default='.')
@click.option('--recursive', is_flag=True, help="Descent through directories")
@click.option('--unzip', is_flag=True, help="Unzip and analyze zipped log files", default=False)

def analyze(codes, agents, genstats, path, recursive, unzip):
    configs = get_configs()
    # get the file list to analyze
    if not os.path.exists(path):
        print("Path doesn't exist!")
        return
    if not os.path.isdir(path):
        files = [path]
    else:
        files = get_list(path, recursive)

    for entry in files:
        log_data = []
        entry_path = entry.split('/')
        file_parts = entry_path[-1].split('.')
        ext = file_parts[-1]
        if ((ext != 'log') and
            (ext != 'bz2')): # not a log file, nor a zipped log file
            continue
        if ext == 'bz2':
            raw_data = sh.bunzip2("-k", "-c", entry)
        else:
            with open(entry) as f:
                raw_data = f.read()
        raw_data_list = raw_data.split('\n')
        print(f"File: {entry} Length: {len(raw_data_list)}")

    all_log_data = []


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