import os
import requests
import yaml

BASE_URL = 'https://api.jujucharms.com/charmstore/v4'
SEARCH_URL = BASE_URL + '/search'

INCLUDES = ['id-name', 'stats', 'manifest']
SERIES = ['trusty', 'xenial']
LIMIT = 3000


def search_url():
    return '{0}?include={1}&series={2}&limit={3}'.format(SEARCH_URL,
        '&include='.join(INCLUDES),
        '&series='.join(SERIES),
        LIMIT)

class Charm(object):
    def __init__(self, charm, data):
        m = data.get('manifest')
        self.files = [f.get('Name') for f in m if isinstance(m, list)]
        self.name = charm.split('/')[-1].rsplit('-', 1)[0]
        self.stats = data.get('stats')
        self.url = charm

    def has_file(self, check):
        return check in self.files


data = requests.get(search_url()).json()
charms = [Charm(c.get('Id'), c.get('Meta')) for c in data.get('Results')]


for charm in charms:
    if not charm.has_file('layer.yaml') and not charm.has_file('reactive/__init__.py'):
        continue

    print charm.name, charm.url, charm.stats['ArchiveDownloadAllRevisions']['Total']
