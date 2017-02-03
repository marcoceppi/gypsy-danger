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


def output_clouds(clouds):
    print("Clouds")
    # sorted_clouds = sorted([(k, v) for k, v in clouds.items()])
    # for k, v in sorted_clouds:
    #     print("    ", k, len(v))


def output_regions(cloud_regions):
    print("Regions")
    # sorted_cloud_regions = sorted([(k, v) for k, v in cloud_regions.items()])
    # for cloud, regions in sorted_cloud_regions:
    #     sorted_regions = sorted([(k, v) for k, v in regions.items()])
    #     print("  ", cloud)
    #     for k, v in sorted_regions:
    #         print("    ", k, len(v))


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
    print("Version\tCount")
    for row in versions:
        print("{0}\t{1}".format(row[0], row[1].decode('utf-8')))


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


@click.command()
@click.option('--init-db', flag_value=True, help='Init the sqlite db')
def main(init_db):
    conn = connect_sql()
    if init_db:
        recreate_db()

        for g in logs:
            print("Found logs {0}".format(len(g)))
            for path in g:
                print("Processing: {0}".format(path))
                logname = os.path.basename(path)
                datestr = logname.\
                    replace('api.jujucharms.com.log-', '').\
                    replace('.anon.gz', '')

                with gzip.open(path) as f:
                    for line in f:
                        if '\n' == line[-1]:
                            line = line[:-1]
                        process_log_line(line, datestr, conn)
            conn.commit()
    else:
        # Don't reload the database, just use what's there.
        pass

    # Output the results of the data
    output_uuids(conn)
    output_latest_day_uuids(conn)
    output_model_ages(conn, _get_latest_day(conn))
    output_models_per_day(conn)
    output_latest_day_versions(conn)


if __name__ == '__main__':
    main()
