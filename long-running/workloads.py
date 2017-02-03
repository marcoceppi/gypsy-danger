#!/usr/bin/env python2


from collections import defaultdict
import glob
import gzip
import re

logs = [
    glob.glob('../logs/api/1/api.jujucharms.com.log-201*'),
    glob.glob('../logs/api/2/api.jujucharms.com.log-201*'),
]

uuid_re = 'environment_uuid=[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12}'
app_re = 'meta/any\?id=[\w][^&]*'
apps = defaultdict(list)
running = {}


def find_uuid(l):
    m = re.search(uuid_re, l)
    if m:
        uuid = m.group(0)
        return uuid
    else:
        return None


def find_app(l):
    app = re.search(app_re, l)

    found = None
    if app:
        _, found = app.group().split('=')

    return found


def main():

    for g in logs:
        print "Found logs {0}".format(len(g))
        for path in g:
            print "Processing: {0}".format(path)
            with gzip.open(path) as f:
                lines = f.read().split("\n")

            for l in lines:
                uuid = find_uuid(l)
                if uuid:
                    apps[uuid].append(find_app(l))

    print "Found UUIDs"
    print len(apps.keys())
    count_me = 'cs%3A~containers%2Fkubernetes-master'
    final = []
    for uuid, found in apps.iteritems():
        if count_me in found:
            final.append(uuid)
    print len(final)


if __name__ == "__main__":
    main()
