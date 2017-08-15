import re

from collections import namedtuple
from jujubundlelib.references import Reference
from urllib.parse import unquote


uuid_re = b'environment_uuid=[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12}'
cloud_re = b'provider=[^,\"]*'
region_re = b'cloud_region=[^,\"]*'
version_re = b'controller_version=[^,\"]*'
application_re = b'[&?]id=[^&,\"]*'
channel_re = b'[&?]channel=[^&,\"]*'

Application = namedtuple(
    'Application', 'charmid, appname, series, owner, channel')
Metadata = namedtuple(
    'Metadata', 'version, cloud, region')
LogLine = namedtuple('LogLine', 'uuid, date, Application, Metadata')


def find_uuid(l):
    m = re.search(uuid_re, l)
    if m:
        uuid = m.group(0)
        # Make sure to decode the uuid or else sqlite won't be able to filter
        # it in bytes.
        var = uuid.split(b'=')[1].decode('utf-8')
        return var
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

    found = Metadata(version.decode('utf-8'),
                     cloud.decode('utf-8'),
                     region.decode('utf-8'))
    return found


def find_application(l):
    """Process a log line looking for the application id"""
    # We also need to return a root "appname" so we can tell how many of an
    # application is out there regardless of the owner/etc.
    charmid = None
    series = None
    channel = None
    appname = None
    owner = None
    app_raw = re.search(application_re, l)
    if app_raw:
        _, charmid = app_raw.group().split(b'=')
        charmid = unquote(charmid.decode("utf-8"))

        # Use the jujubundlelib to parse the charm url for the series
        try:
            ref = Reference.from_string(charmid)
        except ValueError:
            # skip things if there's an error parsing the charm url
            print ('Could not properly parse: {}'.format(charmid))
            return None
        series = ref.series
        appname = ref.name
        owner = ref.user if ref.user else None

        channel_found = re.search(channel_re, l)
        if channel_found:
            _, channel = channel_found.group().split(b'=')
            channel = channel.decode('utf-8')

    found = Application(charmid, appname, series, owner, channel)
    return found


def process_log_line(l, date):
    uuid = find_uuid(l)
    meta = find_metadata(l)
    app = find_application(l)
    # There's multiple log lines, one for each charmid that's requested so
    # we only load the uuid hit once, but we load the application found
    # regardless of if there's a previous uuid row like above.
    return LogLine(uuid, date, app, meta)

        # if app:
        #     c.execute('''
        #         INSERT OR REPLACE INTO application_hits (
        #             uuid,charmid,appname,series,owner,channel,day)
        #         VALUES (?, ?, ?, ?, ?, ?, ?);''', [
        #         uuid, app.charmid, app.appname, app.series, app.owner,
        #         app.channel, date])
        #
        # c.execute('''
        #     INSERT OR REPLACE INTO model_hits (uuid, version, day)
        #     VALUES (?, ?, ?);''', [uuid, meta[0], date])
