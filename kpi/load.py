#!/usr/bin/env python3

import click
import glob
import gzip
import os
import pymysql
import re

from collections import namedtuple
from apachelog import process_log_line


logs = [
    glob.glob('logs/api/1/api.jujucharms.com.log-201*'),
    glob.glob('logs/api/2/api.jujucharms.com.log-201*'),
]

clouds = {}
cloud_regions = {}
versions = {}
running = {}


uuid_re = b'environment_uuid=[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12}'
DB_NAME = 'jujukpi'
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
Application = namedtuple(
    'Application', 'charmid, appname, series, owner, channel')


def connect_sql(host, username, passwd):
    """
    psql
    create database jujukpi;
    \connect kpi
    \password postgres
    """
    conn = pymysql.connect(
        db=DB_NAME, user=username, password=passwd, host=host)
    return conn


def recreate_db(conn):
    """Drop tables and recreate them to reset the sqlite db.


    """
    c = conn.cursor()
    # drop tables if they exist
    c.execute('DROP TABLE IF EXISTS models')
    c.execute('DROP TABLE IF EXISTS model_hits')
    c.execute('DROP TABLE IF EXISTS loaded_logs')
    c.execute('DROP TABLE IF EXISTS application_hits')
    # Save (commit) the changes
    conn.commit()

    c = conn.cursor()
    c.execute('''
        CREATE TABLE models (
        uuid varchar(255) PRIMARY KEY,
        cloud varchar(255),
        region varchar(255))''')
    c.execute('''
        CREATE TABLE model_hits (
        uuid varchar(255),
        day timestamp,
        version varchar(255),
        PRIMARY KEY (uuid, day))''')
    c.execute('''
        CREATE TABLE loaded_logs (
        logfile varchar(255),
        started boolean,
        finished boolean,
        PRIMARY KEY (logfile))''')
    c.execute('''
        CREATE TABLE application_hits (
        uuid varchar(255),
        charmid varchar(255),
        appname varchar(255),
        series varchar(255),
        owner varchar(255),
        channel varchar(255),
        day timestamp,
        PRIMARY KEY (uuid, charmid, day))''')

    conn.commit()


def load_logfiles(conn):
    logs.sort()
    for g in logs:
        print("Found logs {0}".format(len(g)))
        for path in g:
            print("Processing: {0}".format(path))
            path_parts = path.split('/')
            logname = os.path.basename(path)

            datestr = logname.\
                replace('api.jujucharms.com.log-', '').\
                replace('.anon', '').\
                replace('.gz', '')

            c = conn.cursor()
            filename = '/'.join([path_parts[-2], logname])
            c.execute('''
                SELECT * FROM loaded_logs
                WHERE logfile = %s
                ''', (filename, ))
            if c.fetchone() is not None:
                print('Skipping loaded logfile {}'.format(logname))
                continue

            c.execute('''INSERT INTO loaded_logs (
                        logfile, started, finished) VALUES (
                        %s, %s, %s
                        )''', ['/'.join([path_parts[-2], logname]),
                               True,
                               False])
            conn.commit()
            with gzip.open(path) as f:
                c = conn.cursor()
                count = 0
                dupes = []
                model_hits = []
                for line in f:
                    m = re.search(uuid_re, line)
                    if m:
                        count = count + 1
                        if count % 100 == 0:
                            print(count)
                        if '\n' == line[-1]:
                            line = line[:-1]
                        hit = process_log_line(line, datestr)
                        if hit not in dupes:
                            # See if we already have the uuid in the db
                            c.execute(
                                'SELECT uuid FROM models where uuid=%s',
                                [hit.uuid])
                            if c.fetchone() is None:
                                # Add this as a first entry for this model uuid
                                c.execute('''
                                    INSERT IGNORE INTO models
                                        (uuid,cloud,region)
                                    VALUES (%s, %s, %s)
                                    ''', [hit.uuid,
                                          hit.Metadata.cloud,
                                          hit.Metadata.region])

                            if (hit.uuid, hit.date) not in model_hits:
                                c.execute('''
                                    INSERT IGNORE INTO model_hits
                                        (uuid, version, day)
                                    VALUES (%s, %s, %s)
                                    ''', [
                                    hit.uuid,
                                    hit.Metadata.version,
                                    hit.date])
                                model_hits.append((hit.uuid, hit.date))

                            # There's multiple log lines, one for each charmid
                            # that's requested so we only load the uuid hit
                            # once, but we load the application found
                            # regardless of if there's a previous uuid row
                            # like above.
                            if hit.Application is not None and hit.Application.appname:
                                c.execute('''
                                INSERT IGNORE INTO application_hits (
                                    uuid,charmid,appname,series,owner,
                                    channel,day)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                    ''', [
                                    hit.uuid,
                                    hit.Application.charmid,
                                    hit.Application.appname,
                                    hit.Application.series,
                                    hit.Application.owner,
                                    hit.Application.channel,
                                    hit.date])

                            dupes.append(hit)

            c.execute('''UPDATE loaded_logs
                        SET finished=%s
                        WHERE logfile=%s''',
                      [True, path])

            conn.commit()


@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    pass


@cli.command(help="Load new log files that are found from get_logs.")
@click.option('--host', help='The postgresql hostname/address')
@click.option('--passwd',
              prompt='Your passwd',
              help='The postgres user password')
def updatedb(*args, **kwargs):
    """
        Update the db with the log files in /logs/api/xxxx
        To get the MySQL charm password:
        sudo cat /var/lib/mysql/mysql.passwd
    """
    host = kwargs.get('host', None)
    username = 'root'
    passwd = kwargs.get('passwd', None)
    conn = connect_sql(host, username, passwd)
    load_logfiles(conn)
    conn.close()


@cli.command(help="Drop the DB and recreate from log files")
@click.option('--host', help='The postgresql hostname/address')
@click.option('--passwd',
              prompt='Your passwd',
              help='The postgres user password')
def initdb(*args, **kwargs):
    host = kwargs.get('host', None)
    username = 'root'
    passwd = kwargs.get('passwd', None)
    passwd = '2bc933ae-38e2-4606-a5a0-35a814ab9f5f'
    conn = connect_sql(host, username, passwd)
    recreate_db(conn)
    conn.close()


if __name__ == "__main__":
    cli()
