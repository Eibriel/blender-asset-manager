#!/usr/bin/env python3
# ***** BEGIN GPL LICENSE BLOCK *****
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# ***** END GPL LICENCE BLOCK *****

import os
import svn.local
import pprint

from flask import Flask, jsonify, abort, request, make_response, url_for, Response
from flask.views import MethodView
from flask.ext.restful import Api, Resource, reqparse, fields, marshal
from flask.ext.httpauth import HTTPBasicAuth

app = Flask(__name__)
api = Api(app)
auth = HTTPBasicAuth()
import config
app.config.from_object(config.Development)

@api.representation('application/octet-stream')
def output_file(data, code, headers=None):
    """Makes a Flask response to return a file."""
    resp = make_response(data, code)
    resp.headers.extend(headers or {})
    return resp


@auth.get_password
def get_password(username):
    if username == 'bam':
        return 'bam'
    return None


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'message': 'Unauthorized access'}), 403)
    # return 403 instead of 401 to prevent browsers from displaying
    # the default auth dialog


class FilesListAPI(Resource):
    """Displays list of files."""

    decorators = [auth.login_required]

    def __init__(self):
        parser = reqparse.RequestParser()
        #parser.add_argument('rate', type=int, help='Rate cannot be converted')
        parser.add_argument('path', type=str)
        args = parser.parse_args()
        super(FilesListAPI, self).__init__()

    def get(self):

        path = request.args['path']
        if not path:
            path = ''

        absolute_path_root = app.config['STORAGE_PATH']
        parent_path = ''

        if path != '':
            absolute_path_root = os.path.join(absolute_path_root, path)
            parent_path = os.pardir

        items_list = []

        for f in os.listdir(absolute_path_root):
            relative_path = os.path.join(path, f)
            absolute_path = os.path.join(absolute_path_root, f)

            if os.path.isdir(absolute_path):
                items_list.append((f, relative_path, 'folder'))
            else:
                items_list.append((f, relative_path, 'file'))

        project_files = dict(
            parent_path=parent_path,
            items_list=items_list)

        return jsonify(project_files)
        #return {'message': 'Display files list'}


class FileAPI(Resource):
    """Gives acces to a file."""

    decorators = [auth.login_required]

    def __init__(self):
        parser = reqparse.RequestParser()
        parser.add_argument('filepath', type=str, required=True,
            help="Filepath cannot be blank!")
        parser.add_argument('command', type=str, required=True,
            help="Command cannot be blank!")
        args = parser.parse_args()

        super(FileAPI, self).__init__()

    def get(self):
        filepath = request.args['filepath']
        command = request.args['command']

        if command == 'info':
            r = svn.local.LocalClient(app.config['STORAGE_PATH'])

            log = r.log_default(None, None, 5, filepath)
            log = [l for l in log]

            return jsonify(
                filepath=filepath,
                log=log)

        elif command == 'checkout':
            filepath = os.path.join(app.config['STORAGE_PATH'], request.args['filepath'])
            f = open(filepath, 'rb')
            return Response(f, direct_passthrough=True)

        else:
            return jsonify(message='Command unknown')


class FileDepsAPI(Resource):
    """Downloads a file and its deps."""

    decorators = [auth.login_required]

    def __init__(self):
        parser = reqparse.RequestParser()
        parser.add_argument('filepath', type=str, required=True,
            help="Filepath cannot be blank!")
        args = parser.parse_args()

        super(FileDepsAPI, self).__init__()

    def get(self):
        filepath = os.path.join(app.config['STORAGE_PATH'], request.args['filepath'])

        # pack the file!
        print("PACKING")
        filepath_zip = self.pack_fn(filepath)

        # TODO, handle fail
        if filepath_zip is None:
            pass

        f = open(filepath_zip, 'rb')
        return Response(f, direct_passthrough=True)

    @staticmethod
    def pack_fn(filepath):
        import tempfile
        filepath_zip = tempfile.mkstemp(suffix=".zip")

        import os
        modpath = \
            os.path.normpath(
            os.path.abspath(
            os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "packer")))

        import sys
        if modpath not in sys.path:
            sys.path.append(modpath)
        del modpath

        import packer

        print("AAA", filepath)
        print("NNN", filepath_zip)

        try:
            packer.pack(filepath.encode('utf-8'), filepath_zip[-1].encode('utf-8'), mode='ZIP')
            return filepath_zip[-1]
        except:
            import traceback
            traceback.print_exc()

            return None



api.add_resource(FilesListAPI, '/file_list', endpoint='file_list')
api.add_resource(FileAPI, '/file', endpoint='file')
api.add_resource(FileDepsAPI, '/file_deps', endpoint='file_deps')
