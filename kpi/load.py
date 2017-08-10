#!/usr/bin/env python3

import click
import glob
import gzip
import os
import psycopg2
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
    conn = psycopg2.connect(
        dbname=DB_NAME, user=username, password=passwd, host=host)
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
        uuid text PRIMARY KEY,
        cloud text,
        region text)''')
    c.execute('''
        CREATE TABLE model_hits (
        uuid text,
        day text,
        version text,
        PRIMARY KEY (uuid, day))''')
    c.execute('''
        CREATE TABLE loaded_logs (
        logfile text,
        started boolean,
        finished boolean,
        PRIMARY KEY (logfile))''')
    c.execute('''
        CREATE TABLE application_hits (
        uuid text,
        charmid text,
        appname text,
        series text,
        owner text,
        channel text,
        day text,
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
            res = c.execute('''
                SELECT * FROM loaded_logs
                WHERE logfile = %s
            ''', (filename, ))
            found = None
            if res is not None:
                found = res.fetchone()

            if found:
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
                                    INSERT INTO models (uuid,cloud,region)
                                    VALUES (%s, %s, %s)
                                    ''', [hit.uuid,
                                          hit.Metadata.cloud,
                                          hit.Metadata.region])

                            if (hit.uuid, hit.date) not in model_hits:
                                c.execute('''
                                    INSERT INTO model_hits (uuid, version, day)
                                    VALUES (%s, %s, %s)
                                    ON CONFLICT (uuid, day)
                                    DO NOTHING
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
                            if hit.Application.appname:
                                c.execute('''
                                INSERT INTO application_hits (
                                    uuid,charmid,appname,series,owner,
                                    channel,day)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (uuid, charmid, day)
                                DO NOTHING
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


def count_uuids(conn, day=None):
    c = conn.cursor()
    sql = "SELECT COUNT(models.uuid) from models"
    if day:
        sql = '''{}
            INNER JOIN model_hits
            WHERE models.uuid=model_hits.uuid AND model_hits.day=?
        '''.format(sql)
        res = c.execute(sql, [day])
    else:
        res = c.execute(sql)
    return res.fetchone()[0]


def count_versions(conn, day=None):
    c = conn.cursor()
    add_and = ''
    if day:
        add_and = 'AND model_hits.day=?'

    sql = """
        SELECT COUNT(models.uuid), version
        from models
        INNER JOIN model_hits
        WHERE models.uuid=model_hits.uuid {}
        GROUP BY version
        ORDER BY version;
    """
    sql = sql.format(add_and)

    if day:
        res = c.execute(sql, [day])
    else:
        res = c.execute(sql)
    return res.fetchall()


def count_clouds(conn, day=None):
    c = conn.cursor()
    add_and = ''
    if day:
        add_and = 'AND model_hits.day=?'

    sql = """
        SELECT COUNT(models.uuid), cloud from models
        INNER JOIN model_hits
        WHERE models.uuid=model_hits.uuid {}
        GROUP BY cloud
        ORDER BY cloud;
    """
    sql = sql.format(add_and)

    if day:
        res = c.execute(sql, [day])
    else:
        res = c.execute(sql)
    return res.fetchall()


def count_cloud_regions(conn, day=None):
    c = conn.cursor()
    add_and = ''
    if day:
        add_and = 'AND model_hits.day=?'

    sql = """
        SELECT COUNT(models.uuid), cloud, region from models
        INNER JOIN model_hits
        WHERE models.uuid=model_hits.uuid {}
        GROUP BY cloud, region
        ORDER BY cloud, region;
    """
    sql = sql.format(add_and)

    if day:
        res = c.execute(sql, [day])
    else:
        res = c.execute(sql)
    return res.fetchall()


def _get_latest_day(conn):
    c = conn.cursor()
    sql = "SELECT day FROM model_hits ORDER BY day DESC LIMIT 1;"
    res = c.execute(sql).fetchone()
    return res[0]


def output_uuids(conn):
    print('Total Unique UUIDs {}'.format(count_uuids(conn)))


def output_latest_day_uuids(conn):
    day = _get_latest_day(conn)
    count = count_uuids(conn, day=day)
    print("\n\n{} saw {} unique models".format(day, count))


def output_latest_day_versions(conn):
    day = _get_latest_day(conn)
    versions = count_versions(conn, day=day)
    print("\n\n{} saw:".format(day))
    print("Count\tVersion")
    for row in versions:
        print("{0}\t{1}".format(row[0], row[1]))


def output_latest_day_clouds(conn):
    day = _get_latest_day(conn)
    clouds = count_clouds(conn, day=day)
    print("\n\n{} saw:".format(day))
    print("Count\tCloud")
    for row in clouds:
        print("{0}\t{1}".format(row[0], row[1]))


def output_latest_day_cloud_regions(conn):
    day = _get_latest_day(conn)
    clouds = count_cloud_regions(conn, day=day)
    print("\n\n{} saw:".format(day))
    print("Count\tCloud")
    cloud = None
    for row in clouds:
        if cloud != row[1]:
            print('Cloud: ', row[1])
            cloud = row[1]
        print("\t{0}\t{1}".format(row[0], row[2]))


def output_model_ages(conn, day):
    c = conn.cursor()
    sql = '''
        SELECT count(uuid), running
        FROM (
            SELECT model_hits.uuid, count(model_hits.day) as running
            FROM models, model_hits
            WHERE models.uuid = model_hits.uuid
            GROUP BY model_hits.uuid
            HAVING model_hits.day=?)
        GROUP BY running
        ORDER BY running DESC;'''
    res = c.execute(sql, [day]).fetchall()
    print("\n\n")
    print("Ages of models seen on {}".format(day))
    for r in res:
        print('{} models were {} days old'.format(r[0], r[1]))


def output_models_per_day(conn):
    c = conn.cursor()
    sql = '''
        SELECT count(model_hits.uuid), model_hits.day
        FROM model_hits
        GROUP BY model_hits.day
        ORDER BY model_hits.day ASC
    '''
    res = c.execute(sql).fetchall()
    print("\n\n")
    print("Number of models seen each day.")
    print("Date\t\tCount")
    for r in res:
        print("{}\t{}".format(r[1], r[0]))


@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    pass


@cli.command(help="Load new log files that are found from get_logs.")
def updatedb(*args, **kwargs):
    load_logfiles()


@cli.command(help="Drop the DB and recreate from log files")
@click.option('--host', help='The postgresql hostname/address')
@click.option('--passwd',
              prompt='Your passwd',
              help='The postgres user password')
def initdb(*args, **kwargs):
    host = kwargs.get('host', None)
    username = 'postgres'
    passwd = kwargs.get('passwd', None)
    conn = connect_sql(host, username, passwd)
    recreate_db(conn)
    load_logfiles(conn)


@cli.group(help="Grab latest data from the database.")
def run():
    pass


@run.command('summary', help="Model count summary")
def summary():
    conn = connect_sql()
    output_uuids(conn)


@run.command('latest-summary', help="Model count summary from latest day")
def latest_summary():
    conn = connect_sql()
    output_latest_day_uuids(conn)


@run.command('model-ages', help="How long have models been up")
def model_ages():
    conn = connect_sql()
    output_model_ages(conn, _get_latest_day(conn))


@run.command('models-per-day', help="How many models seen per day")
def models_per_day():
    conn = connect_sql()
    output_models_per_day(conn)


@run.command('latest-versions', help="Latest day's summary of Juju versions")
def latest_versions():
    conn = connect_sql()
    output_latest_day_versions(conn)


@run.command('latest-clouds',
             help="Latest day's summary of clouds models are on")
def latest_clouds():
    conn = connect_sql()
    output_latest_day_clouds(conn)


@run.command('latest-clouds-regions',
             help="Latest day's summary of clouds/regions models are on")
def latest_clouds_regions():
    conn = connect_sql()
    output_latest_day_cloud_regions(conn)


if __name__ == "__main__":
    cli()
