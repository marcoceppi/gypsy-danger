# coding: utf-8

import sys
import requests

month=sys.argv[1]
start=sys.argv[2]
end=sys.argv[3]

users = set()
messages = 0

for day in range(int(start), int(end)):
    if len(str(day)) < 2:
        day = '0%s' % day
    if len(str(month)) < 2:
        month = '0%s' % month

    day = str(day)
    month = str(month)

    log = requests.get('http://irclogs.ubuntu.com/2015/{1}/{0}/%23juju.txt'.format(day, month))
    data = log.text.split('\n')
    for line in data:
        if not line.startswith('['):
            continue
        time, user, _ = line.split(' ', 2)
        messages += 1
        users.add(user)

print(len(users))
print(messages)
