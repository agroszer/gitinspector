# coding: utf-8
#
# Copyright © 2014-2026 Ejwa Hosting AB. All rights reserved.
#
# This file is part of gitinspector.
#
# gitinspector is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gitinspector is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gitinspector. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import os
import shutil
import subprocess
import sys
import tempfile

try:
	from urllib.parse import urlparse
except:
	from urlparse import urlparse

__cloned_paths__ = []

class Repository(object):
	def __init__(self, name, location, repo_type="git"):
		self.name = name
		self.location = location
		self.branch = None
		self.repo_type = repo_type

def create(url):
	parsed_url = urlparse(url)

	if parsed_url.scheme in ["file", "git", "http", "https", "ssh", "svn", "svn+ssh"]:
		path = tempfile.mkdtemp(suffix=".gitinspector")

		if parsed_url.scheme in ["svn", "svn+ssh"]:
			svn_co = subprocess.Popen(["svn", "checkout", url, path], stdout=sys.stderr)
			svn_co.wait()

			if svn_co.returncode != 0:
				sys.exit(svn_co.returncode)

			__cloned_paths__.append(path)
			return Repository(os.path.basename(parsed_url.path.rstrip("/")), path, repo_type="svn")

		with open(os.devnull, "w") as devnull:
			git_clone = subprocess.Popen(["git", "clone", url, path], stdout=sys.stderr, stderr=devnull)
			git_clone.wait()

		if git_clone.returncode == 0:
			__cloned_paths__.append(path)
			return Repository(os.path.basename(parsed_url.path.rstrip("/")), path, repo_type="git")

		svn_co = subprocess.Popen(["svn", "checkout", url, path], stdout=sys.stderr)
		svn_co.wait()

		if svn_co.returncode == 0:
			__cloned_paths__.append(path)
			return Repository(os.path.basename(parsed_url.path.rstrip("/")), path, repo_type="svn")

		sys.exit(git_clone.returncode)

	return Repository(None, os.path.abspath(url))

def delete():
	for path in __cloned_paths__:
		shutil.rmtree(path, ignore_errors=True)
