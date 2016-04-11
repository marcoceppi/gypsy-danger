import requests


contributors = set()

r = requests.get('https://api.jujucharms.com/charmstore/v4/changes/published?start=2016-04-04&stop=2016-04-10')
updates = r.json()

print('Contributions: %s' % len(updates))

for i in updates:
    contributors.add(i.get('Id').split(':')[1].split('/')[0])

print('Contributors: %s' % len(contributors))
