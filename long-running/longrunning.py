import re
import os
import glob
import datetime


g = glob.glob('../logs/api/api.jujucharms.com.log-2016*.anon')
uuid_re = '(?<=environment_uuid=)[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12}'

running = {}

for path in g:
    d = os.path.basename(path).replace('api.jujucharms.com.log-', '').replace('.anon', '')
    week = datetime.datetime.strptime(d, '%Y%m%d').isocalendar()[1]
    with open(path) as f:
        lines = f.read().split()

    if week not in running:
        running[week] = set()

    for l in lines:
        m = re.search(uuid_re, l)
        if m:
            running[week].add(m.group(0))

for k in running:
    prev = set()

    if k-2 in running:
        prev = running[k-2]
    if k-1 in running:
        prev = prev | running[k-1]
    prev.intersection_update(running[k])
    print(k, len(running[k]), len(prev))
