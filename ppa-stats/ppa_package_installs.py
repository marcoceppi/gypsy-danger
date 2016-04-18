#!/usr/bin/python2.7

from __future__ import print_function

from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime

from launchpadlib.launchpad import Launchpad


def to_datetime(string):
    return datetime.strptime(string, '%Y-%m-%d')


def report_juju_core_installs(owner_name, ppa_name, package_name, since=None):
    lp = Launchpad.login_with(
        'ppa_package_installs.py', service_root='https://api.launchpad.net',
        version='devel')
    juju_team = lp.people[owner_name]
    stable_archive = juju_team.getPPAByName(name=ppa_name)
    packages = stable_archive.getPublishedBinaries(
        binary_name=package_name, created_since_date=since)
    version_counts = defaultdict(int)
    series_counts = defaultdict(int)
    arch_counts = defaultdict(int)
    print("{} downloads from the {} {} PPA".format(
        package_name, owner_name, ppa_name))
    for package in packages:
        name = package.binary_package_name
        package_version = package.binary_package_version
        version, extra = package_version.rsplit('-', 1)
        series = package.distro_arch_series.distroseries.name
        arch = package.distro_arch_series.architecture_tag
        # We could get weekly or monthly download counts by calling
        # package.getDownloadCounts(start_date=x, end_date=y)in a loop.
        downloads = package.getDownloadCount()
        version_counts[version] += downloads
        series_counts[series] += downloads
        arch_counts[arch] += downloads
        print("%s - %s - %7s - %7s : %s" % (
            name, version, series, arch, downloads))
    print("\nVersion summaries")
    for version in sorted(version_counts):
        count = version_counts[version]
        print("%s: %s" % (version, count))
    print("\nSeries summaries")
    for series in sorted(series_counts):
        count = series_counts[series]
        print("%7s: %s" % (series, count))
    print("\nArch summaries")
    for arch in sorted(arch_counts):
        count = arch_counts[arch]
        print("%5s: %s" % (arch, count))


if __name__ == '__main__':
    parser = ArgumentParser('Count package downloads from a PPA.')
    parser.add_argument('--since', type=to_datetime)
    parser.add_argument('owner_name')
    parser.add_argument('ppa_name')
    parser.add_argument('package_name')
    args = parser.parse_args()
    report_juju_core_installs(
        args.owner_name, args.ppa_name, args.package_name, since=args.since)
