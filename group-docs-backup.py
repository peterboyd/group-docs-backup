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
   documents in the script folder, so they can be backed up or added and managed by
   git, hg, svn etc
"""


import os
import sys
import json
import urllib2
import BaseHTTPServer
import webbrowser
import string

from urlparse import urlparse, parse_qs
from urllib import urlencode

__authors__ = "Peter Boyd"
__copyright__ = "Copyright 2012, Peter Boyd"
__license__ = "GPL"
__version__ = "0.1"
__maintainer__ = "Peter Boyd"
__status__ = "Development"


APP_ID = '205214459571218'
APP_NAME = "Group Docs Backup"
GROUPS_ID = ('2204510018','228135853929943') # Linux and Linux (tech support) groups
SERVER_IP = "127.0.0.1"
SERVER_PORT = 8080
REDIRECT_URI = 'http://%s:%s/' % (SERVER_IP,SERVER_PORT)
ACCESS_TOKEN = None
AUTH_SCOPE = ['user_groups', 'offline_access']
LOCAL_FILE = os.environ["HOME"] + '/.fb_access_token'
SCRIPT_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))

__all__ = [
    'help',
    'authenticate',
    'graph',
    'APP_ID',
    'APP_NAME',
    'GROUPS_ID',
    'SERVER_IP',
    'SERVER_PORT',
    'ACCESS_TOKEN',
    'AUTH_SCOPE',
    'SCRIPT_DIR',
    'LOCAL_FILE']

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
                print  "Error creating: %s" % LOCAL_FILE
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
    """Authenticate with Facebook so you can make API calls that require auth.

    Alternatively you can just set the ACCESS_TOKEN global variable in this
    module to an access token you get from facebook.

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
            print "Local Facebook Authorisation file problem. We need re-authentication..."
            try:
                os.remove(LOCAL_FILE)
            except:
                print  "Error deleting: %s" % LOCAL_FILE
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
    print "\nGeting Docs data for Group ID: %s..." % groupID

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
        - create group ID folders
        - get all the docs data from each group
        - writes every doc with the name ID.html
        - prompts for adding to git, hg etc
    """
    global ACCESS_TOKEN

    authenticate()

    for gid in GROUPS_ID:
        # We use Group ID for the folder names because Group Name may change
        GROUP_DIR = SCRIPT_DIR + '/' + gid
        if not os.path.exists(GROUP_DIR):
            try:
                os.makedirs(GROUP_DIR)
            except:
                print  "Error creating Group ID folder: %s" % GROUP_DIR
                print  sys.exc_info()
            else:
                print "\nCreated folder for Group ID: %s" % gid

        json_data = graph(gid, "/%s/docs" % gid, {'fields':'id,subject,message'})

        while 'error' in json_data.keys():
            print "Authorisation problem: " + str(json_data['error'])
            print "Trying to reauthorise the application on Facebook..."

            try:
                os.remove(LOCAL_FILE)
            except:
                print  "Error deleting: %s" % LOCAL_FILE
                print  sys.exc_info()

            ACCESS_TOKEN = None
            authenticate()
            json_data = graph(gid, "/%s/docs" % gid, {'fields':'id,subject,message'})

        doc = json_data['data']

        if not doc: # If data is empty, it means we are not allowed to read group docs
            print "You are not Authorised to read the Docs section of the Group with ID: %s" % gid
            print "No documents will be downloaded for this group!"
            print "Go to Facebook and join the group first please."


        for entry in doc:
            try:
                f = open(GROUP_DIR + '/' + entry['id'] + '.html','w')
                f.write(u'TITLE: '+ entry['subject'] + u'\r\n\r\n<br><br>' + string.replace(entry['message'].encode('UTF-8'), '\xc2\xa0', ''))
                f.close()
            except:
                print  "Error creating Document ID: %s" % entry['id'] + '.html'
                print  sys.exc_info()
            else:
                print "Created Document ID: %s" % entry['id'] + '.html'

    print "\nJob done."
    print "Do not forget to add the folder -> %s <- to your git, hg,svn etc repo\n" % SCRIPT_DIR

if __name__ == '__main__':
    main()
