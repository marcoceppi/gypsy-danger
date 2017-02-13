#!/usr/bin/env python3

import click
import glob
import gzip
import os
import re
import sqlite3


logs = [
    glob.glob('logs/api/1/api.jujucharms.com.log-201*'),
    glob.glob('logs/api/2/api.jujucharms.com.log-201*'),
]

uuid_re = b'environment_uuid=[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12}'
cloud_re = b'provider=[^,\"]*'
region_re = b'cloud_region=[^,\"]*'
version_re = b'controller_version=[^,\"]*'
clouds = {}
cloud_regions = {}
versions = {}
running = {}


DB_NAME = 'models.db'
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def connect_sql():
    conn = sqlite3.connect('models.db')
    return conn


def recreate_db():
    """Simple program that greets NAME for a total of COUNT times."""
    conn = connect_sql()
    c = conn.cursor()
    # drop tables if they exist
    c.execute('DROP TABLE IF EXISTS models')
    c.execute('DROP TABLE IF EXISTS model_hits')
    c.execute('DROP TABLE IF EXISTS loaded_logs')
    # Save (commit) the changes
    conn.commit()

    c = conn.cursor()
    c.execute('''
        CREATE TABLE models (
        uuid text PRIMARY KEY,
        version text,
        cloud text,
        region text)''')
    c.execute('''
        CREATE TABLE model_hits (
        uuid text,
        day text,
        PRIMARY KEY (uuid, day))''')
    c.execute('''
        CREATE TABLE loaded_logs (
        logfile text,
        started boolean,
        finished boolean,
        PRIMARY KEY (logfile))''')

    conn.commit()


def find_uuid(l):
    m = re.search(uuid_re, l)
    if m:
        uuid = m.group(0)
        return uuid.split(b'=')[1]
    else:
        return None


def find_metadata(l):
    c = re.search(cloud_re, l)
    cr = re.search(region_re, l)
    v = re.search(version_re, l)
    cloud = b'pre-2'
    region = b'pre-2'
    version = b'pre-2'

    if c:
        _, cloud = c.group().split(b'=')

    if cr:
        _, region = cr.group().split(b'=')

    if v:
        _, version = v.group().split(b'=')

    return (version, cloud, region)


def process_log_line(l, date, conn):
    uuid = find_uuid(l)
    c = conn.cursor()
    if uuid:
        # See if we already have the uuid in the db
        c.execute('SELECT uuid FROM models where uuid=?', [uuid])
        row = c.fetchone()

        if not row:
            meta = find_metadata(l)
            # Add this as a first entry for this model uuid
            c.execute('''
                INSERT INTO models (uuid,version,cloud,region)
                VALUES (?, ?, ?, ?);''', [uuid, meta[0], meta[1], meta[2]])
        c.execute('''
            INSERT OR REPLACE INTO model_hits (uuid,day)
            VALUES (?, ?);''', [uuid, date])


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
        SELECT COUNT(models.uuid), version from models
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
        print("{0}\t{1}".format(row[0], row[1].decode('utf-8')))


def output_latest_day_clouds(conn):
    day = _get_latest_day(conn)
    clouds = count_clouds(conn, day=day)
    print("\n\n{} saw:".format(day))
    print("Count\tCloud")
    for row in clouds:
        print("{0}\t{1}".format(row[0], row[1].decode('utf-8')))


def output_latest_day_cloud_regions(conn):
    day = _get_latest_day(conn)
    clouds = count_cloud_regions(conn, day=day)
    print("\n\n{} saw:".format(day))
    print("Count\tCloud")
    cloud = None
    for row in clouds:
        if cloud != row[1]:
            print('Cloud: ', row[1].decode('utf-8'))
            cloud = row[1]
        print("\t{0}\t{1}".format(row[0], row[2].decode('utf-8')))


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


@cli.command(help="Drop the DB and recreate from log files")
def initdb():
    conn = connect_sql()
    recreate_db()

    for g in logs:
        print("Found logs {0}".format(len(g)))
        for path in g:
            print("Processing: {0}".format(path))
            path_parts = path.split('/')
            logname = os.path.basename(path)

            datestr = logname.\
                replace('api.jujucharms.com.log-', '').\
                replace('.anon.gz', '')

            c = conn.cursor()
            c.execute('''INSERT INTO loaded_logs (
                        logfile, started, finished) VALUES (
                        ?, ?, ?
                        )''', ['/'.join([path_parts[-2], logname]),
                               True,
                               False])
            conn.commit()

            with gzip.open(path) as f:
                for line in f:
                    if '\n' == line[-1]:
                        line = line[:-1]
                    process_log_line(line, datestr, conn)
            c.execute('''UPDATE loaded_logs
                        SET finished=?
                        WHERE logfile=?''',
                      [True, path])
        conn.commit()


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
