#!/usr/bin/python

from __future__ import print_function

from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime

from launchpadlib.launchpad import Launchpad

running_count = 0


def to_datetime(string):
    return datetime.strptime(string, '%Y-%m-%d')


def report_juju_core_installs(owner_name, ppa_name, package_name, start_date, end_date):
    global running_count
    lp = Launchpad.login_with(
        'ppa_package_installs.py', service_root='https://api.launchpad.net',
        version='devel')
    juju_team = lp.people[owner_name]
    stable_archive = juju_team.getPPAByName(name=ppa_name)
    packages = stable_archive.getPublishedBinaries(
        binary_name=package_name)
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
        download_count = 0
        downloads = package.getDownloadCounts(start_date=start_date, end_date=end_date)
        for download in downloads:
            print("Processing download count for country: %s, day: %s, number: %d" % (download.country, download.day, download.count))
            download_count = download_count + download.count
        #downloads = package.getDownloadCount()
        version_counts[version] += download_count
        series_counts[series] += download_count
        arch_counts[arch] += download_count
        print("%s - %s - %7s - %7s : %s" % (
            name, version, series, arch, download_count))
        running_count = running_count + download_count
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
    print("Total counts for the date range: %d" % running_count)


if __name__ == '__main__':
    parser = ArgumentParser('Count package downloads from a PPA.')
    parser.add_argument('owner_name')
    parser.add_argument('ppa_name')
    parser.add_argument('package_name')
    parser.add_argument('start_date')
    parser.add_argument('end_date')
    args = parser.parse_args()
    report_juju_core_installs(
        args.owner_name, args.ppa_name, args.package_name, args.start_date, args.end_date)
