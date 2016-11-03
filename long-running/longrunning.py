#!/usr/bin/env python2


import datetime
from collections import defaultdict
from collections import namedtuple
import glob
import gzip
import os
import re

Metadata = namedtuple('Metadata', ['cloud', 'region', 'version'])


logs = [
    glob.glob('../logs/api/1/api.jujucharms.com.log-2016*'),
    glob.glob('../logs/api/2/api.jujucharms.com.log-2016*'),
]
uuid_re = 'environment_uuid=[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12}'
cloud_re = 'provider=[^,\"]*'
region_re = 'cloud_region=[^,\"]*'
version_re = 'controller_version=[^,\"]*'
clouds = defaultdict(set)
cloud_regions = defaultdict(set)
versions = defaultdict(set)
running = {}


def find_uuid(l):
    m = re.search(uuid_re, l)
    if m:
        uuid = m.group(0)
        return uuid
    else:
        return None


def find_metadata(l):
    c = re.search(cloud_re, l)
    cr = re.search(region_re, l)
    v = re.search(version_re, l)
    cloud = None
    region = None
    version = None

    if c:
        _, cloud = c.group().split('=')

    if cr:
        _, region = cr.group().split('=')

    if v:
        _, version = v.group().split('=')
    else:
        versions['pre-2'].add(uuid)

    return Metadata(cloud, region, version)


for g in logs:
    print "Found logs {0}".format(len(g))
    for path in g:
        print "Processing: {0}".format(path)
        logname = os.path.basename(path)
        datestr = logname.\
            replace('api.jujucharms.com.log-', '').\
            replace('.anon.gz', '')
        week = datetime.datetime.strptime(datestr, '%Y%m%d').isocalendar()[1]
        with gzip.open(path) as f:
            lines = f.read().split("\n")

        if week not in running:
            running[week] = set()

        for l in lines:
            uuid = find_uuid(l)
            if uuid:
                running[week].add(uuid)
                meta = find_metadata(l)

                # Add that we saw this uuid this week.
                running[week].add(uuid)

                # build the metadata dictionaries
                clouds[meta.cloud].add(uuid)

                if not cloud_regions[meta.cloud]:
                    cloud_regions[meta.cloud] = defaultdict(set)
                cloud_regions[meta.cloud][meta.region].add(uuid)

                versions[meta.version].add(uuid)


def output_clouds(clouds):
    print "Clouds"
    sorted_clouds = sorted([(k, v) for k, v in clouds.items()])
    for k, v in sorted_clouds:
        print "    ", k, len(v)


def output_regions(cloud_regions):
    print "Regions"
    sorted_cloud_regions = sorted([(k, v) for k, v in cloud_regions.items()])
    for cloud, regions in sorted_cloud_regions:
        sorted_regions = sorted([(k, v) for k, v in regions.items()])
        print "  ", cloud
        for k, v in sorted_regions:
            print "    ", k, len(v)


def output_versions(version):
    print "Versions"
    sortedversions = sorted([(k, v) for k, v in versions.items()])
    for k, v in sortedversions:
        print "    ", k, len(v)


def main():

    print "Long running models"
    for k in running:
        prev = set()

        if k-2 in running:
            prev = running[k-2]
        if k-1 in running:
            prev = prev | running[k-1]
        prev.intersection_update(running[k])
        print'Week ', k, len(running[k]), len(prev)

    output_clouds(clouds)
    output_regions(cloud_regions)
    output_versions(versions)


if __name__ == "__main__":
    main()
