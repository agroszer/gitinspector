# coding: utf-8
#
# Copyright © 2012-2026 Ejwa Hosting AB. All rights reserved.
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

import os
import subprocess
import sys

def get_basedir():
	#A frozen build carries the html templates and the translations beside the interpreter it
	#bundles. PyInstaller names that directory in sys._MEIPASS; py2exe only sets sys.prefix.
	if hasattr(sys, "frozen"):
		return getattr(sys, "_MEIPASS", sys.prefix)

	return os.path.dirname(os.path.realpath(__file__))

def get_basedir_git(path=None):
	abs_path, repo_type = get_basedir_and_type(path)
	if repo_type != "git":
		sys.exit(_("Error processing git repository at \"%s\".") % (path if path else os.getcwd()))
	return abs_path

def get_basedir_and_type(path=None):
	previous_directory = None

	if path != None:
		previous_directory = os.getcwd()

		try:
			os.chdir(path)
		except OSError:
			sys.exit(_("Error processing git repository at \"%s\".") % path)

	# Check if git repository
	is_git = False
	isbare = False
	try:
		with open(os.devnull, "w") as devnull:
			bare_command = subprocess.Popen(["git", "rev-parse", "--is-bare-repository"],
			                          stdout=subprocess.PIPE, stderr=devnull)
			bare_out = bare_command.stdout.readlines()
			bare_command.wait()
			if bare_command.returncode == 0:
				is_git = True
				isbare = (bare_out[0].decode("utf-8", "replace").strip() == "true")
	except OSError:
		pass

	if is_git:
		absolute_path = None

		if isbare:
			absolute_path = subprocess.Popen(["git", "rev-parse", "--git-dir"], stdout=subprocess.PIPE).stdout
		else:
			absolute_path = subprocess.Popen(["git", "rev-parse", "--show-toplevel"],
			                                 stdout=subprocess.PIPE).stdout

		absolute_path = absolute_path.readlines()

		if len(absolute_path) == 0:
			sys.exit(_("Unable to determine absolute path of git repository."))

		if path != None:
			os.chdir(previous_directory)

		return absolute_path[0].decode("utf-8", "replace").strip(), "git"

	# Check if svn repository
	is_svn = False
	svn_info = b""
	try:
		with open(os.devnull, "w") as devnull:
			svn_command = subprocess.Popen(["svn", "info"],
			                         stdout=subprocess.PIPE, stderr=devnull)
			svn_info = svn_command.communicate()[0]
			if svn_command.returncode == 0:
				is_svn = True
	except OSError:
		pass

	if is_svn:
		wc_root = None
		for line in svn_info.decode("utf-8", "replace").splitlines():
			if line.startswith("Working Copy Root Path:"):
				wc_root = line.split(":", 1)[1].strip()
				break
		if not wc_root:
			wc_root = os.getcwd()

		if path != None:
			os.chdir(previous_directory)

		return wc_root, "svn"

	if path != None:
		os.chdir(previous_directory)

	sys.exit(_("Error processing git repository at \"%s\".") % (path if path else os.getcwd()))
