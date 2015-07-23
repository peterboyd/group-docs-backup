#! /usr/bin/python
# -*- coding: utf-8 -*-
#
#    group-docs-backup.py - The main application.
#
#    Copyright 2012 - Peter Boyd
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#    MA 02110-1301, USA.
#
#    This program is based on some of the code by Paul Carduner's fbconsole
#    application:
#       http://blog.carduner.net/2011/09/06/easy-facebook-scripting-in-python/
#       https://gist.github.com/1194123#file_fbconsole.py
#    Credits to him.
#

"""This program downloads all available from a selected FB Group
   documents in the script folder, so they can be backed up or added and
   managed by git, hg, svn etc

   Tree content:
        GROUP_ID/ - id folder of the group
            |
            |--deleted/ - folder to keep already deleted Docs (raw and html)
            |
            |--DOC_ID.raw - FB json raw response for the Doc
            |
            |--DOC_ID.html - FB response for the Doc in HTML, so it can be
                             copied/pasted online conveniently
"""


import os
import sys
import glob
import shutil
import codecs

import json
import urllib2
import BaseHTTPServer
import webbrowser

from urlparse import urlparse, parse_qs
from urllib import urlencode

__authors__ = "Peter Boyd"
__copyright__ = "Copyright 2012, Peter Boyd"
__license__ = "GPL"
__version__ = "0.2"
__maintainer__ = "Peter Boyd"
__status__ = "Development"


# You can edit the group IDs if you want
GROUPS_ID = ('2204510018','228135853929943','2371797727') # Linux, Linux (tech support) and CentOS groups


# No need to edit anything below here
APP_ID = '205214459571218'
APP_NAME = "Group Docs Backup"
ACCESS_TOKEN = None
AUTH_SCOPE = ['user_groups']

SERVER_IP = "127.0.0.1"
SERVER_PORT = 8080
REDIRECT_URI = 'http://%s:%s/' % (SERVER_IP,SERVER_PORT)

LOCAL_FILE = os.environ["HOME"] + '/.fb_access_token'
SCRIPT_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))

COLORS = dict(
        list(zip([
            'FAIL',
            'OK',
            'WARN',
            ],
            list(range(31,34))
            ))
        )
RESET = '\033[0m'

HTML = """<!DOCTYPE html>
<html>
    <head>
        <title>%s</title>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" >
    </head>
    <body>
        <b>TITLE OF THE DOCUMENT (just copy/paste it):</b>
        <div style="border: 2px solid; padding: 10px; margin: 10px 50px 50px;">
             %s
        </div>

        <b>CONTENT OF THE DOCUMENT (just copy/paste it):</b>
        <div style="border: 2px solid; padding: 10px; margin: 10px 50px;">
            %s
        </div>
    </body>
</html>
"""

__all__ = [
    'help',
    'authenticate',
    'graph',
    'GROUPS_ID',
    'APP_ID',
    'APP_NAME',
    'ACCESS_TOKEN',
    'AUTH_SCOPE',
    'SERVER_IP',
    'SERVER_PORT',
    'SCRIPT_DIR',
    'LOCAL_FILE'
    'COLORS',
    'RESET',
    'HTML']

def colored(text, color=None):
    """Colorize and bold text.

    Available text colors:
        FAIL (red), OK (green), WARN (yellow), no color is bold only

    Example:
        colored('TEST STRING', 'OK') -> bold green
        colored('TEST STRING') -> bold
    """
    if os.getenv('ANSI_COLORS_DISABLED') is None:
        if color is not None:
            text = '\033[1;%dm%s' % (COLORS[color], text)
        else:
            text = '\033[1m%s' % text

        text += RESET

    return text

def _get_url(path, args=None):
    args = args or {}
    if ACCESS_TOKEN:
        args['access_token'] = ACCESS_TOKEN

    return 'https://graph.facebook.com'+str(path)+'?'+urlencode(args)

class _RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        global ACCESS_TOKEN
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        params = parse_qs(urlparse(self.path).query)
        ACCESS_TOKEN = params.get('access_token', [None])[0]
        if ACCESS_TOKEN:
            data = {'scope': AUTH_SCOPE,
                    'access_token': ACCESS_TOKEN}

            try:
                f = open(LOCAL_FILE,'w')
                f.write(json.dumps(data))
                f.close()
                os.chmod(LOCAL_FILE, 0700)
            except:
                print  colored("Error creating: %s" % LOCAL_FILE, 'FAIL')
                print  sys.exc_info()
            else:
                self.wfile.write('<html><head><title>Login success</title></head>'
                                 '<body><h3>'
                                 '<br>You have successfully logged in to Facebook with <i>' + APP_NAME +
                                 '</i><br>You can close this window now.'
                                 '</h3></body></html>')
        else:
            self.wfile.write('<html><head>'
                             '<script>location = "?"+location.hash.slice(1);</script>'
                             '</head></html>')

def authenticate():
    """Authenticate with Facebook, so you can make API calls that require auth.

    Alternatively you can just set the ACCESS_TOKEN global variable in this
    module to an access token you get from Facebook.

    If you want to request certain permissions, set the AUTH_SCOPE global
    variable to the list of permissions you want.
    """
    print "\nGetting Authentification..."
    global ACCESS_TOKEN
    needs_auth = True
    if os.path.exists(LOCAL_FILE):
        try:
            data = json.loads(open(LOCAL_FILE).read())
        except:
            print colored("Local Facebook Authorisation file problem. We need re-authentication...", 'FAIL')
            try:
                os.remove(LOCAL_FILE)
            except:
                print  colored("Error deleting: %s" % LOCAL_FILE, 'FAIL')
                print  sys.exc_info()

        else:
            if set(data['scope']).issuperset(AUTH_SCOPE):
                ACCESS_TOKEN = data['access_token']
                needs_auth = False

    if needs_auth:
        print "\nStarting local hhtpd to get Facebook response..."
        httpd = BaseHTTPServer.HTTPServer((SERVER_IP, SERVER_PORT), _RequestHandler)
        print "\nLogging you into Facebook..."
        webbrowser.open('https://www.facebook.com/dialog/oauth?' +
                        urlencode({'client_id':APP_ID,
                                   'redirect_uri':REDIRECT_URI,
                                   'response_type':'token',
                                   'scope':','.join(AUTH_SCOPE)}))

        while ACCESS_TOKEN is None:
            httpd.handle_request()

def graph(groupID, path, params=None):
    """Send a GET request to the graph API.

    For example:

      >>> graph('/me')
      >>> graph('/me')['name']
      >>> graph('/me', {'fields':'id,name'})

    """
    print "\nGeting Docs data for Group ID: %s..." % colored(groupID)

    try:
        response = urllib2.urlopen(_get_url(path, args=params))

    except urllib2.HTTPError, e:
        # If we have problems with Auth, or we are not members of the group
        # we get 400 error, but still he have a json response, so pass on
        if e.code == 400:
            response = e
        else:
            raise

    except URLError, e:
        # We may have some net problems so handle them?
        print e.reason
        raise

    return json.load(response)



def main():
    """This is the main method of the application that is called first.

    It does (in order of appearance):
        - authenticate
        - get all the docs data from each group
        - create group ID folders if needed
        - writes every doc with the name ID.raw, so we have raw json data
        - writes every doc with the name ID.html, so we have convenient format
        - checks if any Docs were deleted since last backup. If yes -> creates
          a deleted folder and move the file/s there
        - prompts for adding to git, hg etc
    """
    global ACCESS_TOKEN

    authenticate()

    for gid in GROUPS_ID:
        json_data = graph(gid, "/%s/docs" % gid)

        while 'error' in json_data.keys():
            if str(json_data['error']['type']) != 'OAuthException': # OR == 'GraphMethodException'
                break

            print colored("Authorisation problem: ", 'FAIL') + colored(str(json_data['error']))
            print colored("Trying to reauthorise the application on Facebook...", 'WARN')

            try:
                os.remove(LOCAL_FILE)
            except:
                print  colored("Error deleting: %s" % LOCAL_FILE, 'FAIL')
                print  sys.exc_info()

            ACCESS_TOKEN = None
            authenticate()
            json_data = graph(gid, "/%s/docs" % gid)

        if not 'data' in json_data.keys():
            print colored("There is a problem with Group ID: %s" % gid, 'FAIL')
            print colored("Go to Facebook and check its ID please.", 'WARN')
            print colored("Link to the group: ", 'WARN') + colored('https://www.facebook.com/groups/%s' % gid)
            continue

        doc = json_data['data']

        if not doc: # If data is empty, it means we are not allowed to read group docs
            print colored("No Docs or not Authorised to read the Docs section of the Group with ID: %s" % gid, 'FAIL')
            print colored("No documents will be downloaded for this group!", 'WARN')
            print colored("Go to Facebook and check or join the group first please.", 'WARN')
            print colored("Link to the group: ", 'WARN') + colored('https://www.facebook.com/groups/%s' % gid)

        else:
            # We use Group ID for the folder names because Group Name may change
            GROUP_DIR = SCRIPT_DIR + '/' + gid
            if not os.path.exists(GROUP_DIR):
                try:
                    os.makedirs(GROUP_DIR)
                except:
                    print  colored("Error creating Group ID folder: %s" % GROUP_DIR, 'FAIL')
                    print  sys.exc_info()
                else:
                    print colored("\nCreated folder for Group ID: ", 'OK') + colored(gid)

            # Create a dict of existing files ids, for finding deleted ones since last backup
            file_dict = {}
            for f in glob.glob(GROUP_DIR + '/*.html'):
                file_dict[os.path.basename(os.path.splitext(f)[0])] = 'True'

            for entry in doc:
                # Create a .raw file, for the future when FB implements API fo doc modification
                try:
                    f = codecs.open(GROUP_DIR + '/' + entry['id'] + '.raw','w', encoding='UTF-8')
                    f.write(json.dumps(entry))
                    f.close()
                except:
                    print  colored("Error creating Document ID: %s" % entry['id'] + '.raw', 'FAIL')
                    print  sys.exc_info()
                else:
                    print colored("Created Document ID: ", 'OK') + colored(entry['id'] + '.raw')

                # Create a .html file to easy copy/paste edits of FB doc online
                if not 'message' in entry.keys(): # FB doesn't send 'message' if Doc is empty
                    entry['message'] = ''

                try:
                    f = codecs.open(GROUP_DIR + '/' + entry['id'] + '.html','w', encoding='UTF-8')
                    f.write(HTML % (entry['subject'], entry['subject'], entry['message']))
                    f.close()
                except:
                    print  colored("Error creating Document ID: %s" % entry['id'] + '.html', 'FAIL')
                    print  sys.exc_info()
                else:
                    print colored("Created Document ID: ", 'OK') + colored(entry['id'] + '.html')

                # Remove file id from the dict
                if entry['id'] in file_dict.keys():
                    del file_dict[entry['id']]

            # Check if files are left in dict. If yes, means they were deleted from the last backup
            if len(file_dict) == 0:
                print colored("No Docs since last backup were deleted from this Group with ID: ", 'OK') + colored(gid)
            else:
                print colored("Found Docs deleted since last backup from this Group with ID: %s" % gid, 'FAIL')

                # Create a Group ID "deleted" folder to keep deleted files available
                GROUP_DIR_DELETED = GROUP_DIR + '/deleted'
                if not os.path.exists(GROUP_DIR_DELETED):
                    try:
                        os.makedirs(GROUP_DIR_DELETED)
                    except:
                        print  colored("Error creating folder for deleted files in Group ID: %s" % GROUP_DIR_DELETED, 'FAIL')
                        print  sys.exc_info()
                    else:
                        print colored("\nCreated folder for deleted files in Group ID: ", 'OK') + colored(gid)

                print colored("\nMoving all deleted files to the deleted folder of Group ID: ", 'OK') + colored(gid)

                for f_deleted in file_dict.keys():
                    data_raw = {}
                    try:
                        data_raw = json.loads(open(GROUP_DIR + '/' + f_deleted + '.raw').read())
                    except:
                        print colored("Cannot read the deleted Doc with ID: %s" % f_deleted, 'FAIL')
                        data_raw['subject'] = 'UNKNOWN SUBJECT'

                    print colored("DELETED: ", 'FAIL') + colored(f_deleted + '-> ' + data_raw['subject'])

                    # Move all deleted files in GROUP_DIR_DELETED
                    for f in glob.glob(GROUP_DIR + '/' + f_deleted + '.*'):
                        try:
                            shutil.move(f, GROUP_DIR_DELETED + '/' + os.path.basename(f))
                        except:
                            print  colored("Error moving file %s to folder: %s" % (f, GROUP_DIR_DELETED), 'FAIL')
                            print  sys.exc_info()


    print colored("\nJob done.", 'OK')
    print colored("Do not forget to update your local&remote git, hg, svn etc repo\n", 'WARN')

if __name__ == '__main__':
    main()
