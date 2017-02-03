#!/usr/bin/env python2


from datetime import datetime
from collections import defaultdict
from collections import namedtuple
from collections import OrderedDict
import glob
import gzip
import os
import re

Record = namedtuple('Record', ['uuid', 'cloud', 'region', 'version'])

logs = [
    glob.glob('../logs/api/1/api.jujucharms.com.log-201*'),
    glob.glob('../logs/api/2/api.jujucharms.com.log-201*'),
]
uuid_re = 'environment_uuid=[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12}'
cloud_re = 'provider=[^,\"]*'
region_re = 'cloud_region=[^,\"]*'
version_re = 'controller_version=[^,\"]*'
clouds = {}
cloud_regions = {}
versions = {}
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
    cloud = 'pre-2'
    region = 'pre-2'
    version = 'pre-2'

    if c:
        _, cloud = c.group().split('=')

    if cr:
        _, region = cr.group().split('=')

    if v:
        _, version = v.group().split('=')

    return (cloud, region, version)


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
    sortedversions = sorted([(k, v) for k, v in version.items()])

    for k, v in sortedversions:
        print "    ", k, len(v)


def process_log_line(l, week):
    uuid = find_uuid(l)
    if uuid:
        meta = find_metadata(l)
        record = Record(uuid, meta[0], meta[1], meta[2])

        # Add that we saw this uuid this week.
        running[week].add(record.uuid)
        if week not in clouds:
            clouds[week] = defaultdict(set)
        clouds[week][record.cloud].add(uuid)

        if week not in cloud_regions:
            cloud_regions[week] = defaultdict(set)
        if not cloud_regions[week][record.cloud]:
            cloud_regions[week][record.cloud] = defaultdict(set)
        cloud_regions[week][record.cloud][record.region].add(uuid)

        if week not in versions:
            versions[week] = defaultdict(set)
        versions[week][record.version].add(uuid)


def main():
    week_list = OrderedDict()
    # Track the datestr for the running week.It should be the sunday of the
    # week and we reuse that for each day in that week to group/aggregate the
    # weeks.
    running_datestr = ''
    for g in logs:
        print "Found logs {0}".format(len(g))
        for path in g:
            print "Processing: {0}".format(path)
            logname = os.path.basename(path)
            datestr = logname.\
                replace('api.jujucharms.com.log-', '').\
                replace('.anon.gz', '')
            week = datetime.strptime(datestr, '%Y%m%d').isocalendar()[1]

            with gzip.open(path) as f:
                lines = f.read().split("\n")

            if week not in week_list.values():
                # We've hit a new numerical week (1-52) so we need to update
                # the running datestr to this new sunday date and make sure we
                # log we've seen this week under this datestr.
                running_datestr = datestr
                week_list[datestr] = week
                running[running_datestr] = set()

            for l in lines:
                process_log_line(l, running_datestr)

    unique_uuids = set()
    for w in running.values():
        unique_uuids.update(w)
    print "Total UUIDs"
    print len(unique_uuids)

    print "Cloud and Version info"
    print "Week    \tCount\tRepeats"
    for datestr, week in week_list.items():
        print datestr
        output_clouds(clouds[datestr])
        output_regions(cloud_regions[datestr])
        output_versions(versions[datestr])

    print "Long running models"
    print "Week    \tCount\tRepeats"
    for datestr, week in week_list.items():
        prev = set()

        if week == 1:
            # Only 52 weeks in a year so if we hit week one time to go back to
            # the last week of the year for our numbers.
            prev1 = 52
        else:
            prev1 = week-1

        if prev1 in week_list.values():
            for ds, w in week_list.items():
                if w == prev1:
                    datestr1 = ds
            prev = running[datestr1]
            prev.intersection_update(running[datestr])
            print datestr, "\t", len(running[datestr]), "\t", len(prev)
        else:
            # Let it go
            pass


if __name__ == "__main__":
    main()
