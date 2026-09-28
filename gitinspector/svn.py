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

from __future__ import unicode_literals
import calendar
import datetime
import os
import subprocess
import xml.etree.ElementTree as ET

def decode(output):
	try:
		return output.decode("utf-8")
	except UnicodeDecodeError:
		return output.decode("latin-1")

def __output_of__(command, location):
	with open(os.devnull, "w") as devnull:
		process = subprocess.Popen(command, cwd=location, stdout=subprocess.PIPE, stderr=devnull)
		return decode(process.communicate()[0]).strip()

def is_available():
	try:
		__output_of__(["svn", "--version"], None)
		return True
	except OSError:
		return False

def is_svn_repository(location):
	try:
		with open(os.devnull, "w") as devnull:
			process = subprocess.Popen(["svn", "info"], cwd=location, stdout=subprocess.PIPE, stderr=devnull)
			process.communicate()
			return process.returncode == 0
	except OSError:
		return False

def get_branch(location):
	try:
		info = __output_of__(["svn", "info"], location)
		for line in info.splitlines():
			if line.startswith("Relative URL:"):
				rel_url = line.split(":", 1)[1].strip()
				return rel_url.lstrip("^/")
			elif line.startswith("URL:"):
				url = line.split(":", 1)[1].strip()
				return os.path.basename(url)
	except Exception:
		pass
	return None

def get_files(location):
	files = []
	try:
		out = __output_of__(["svn", "list", "-R"], location)
		for line in out.splitlines():
			line = line.strip()
			if line and not line.endswith("/"):
				if os.path.isfile(os.path.join(location, line)):
					files.append(line)
	except Exception:
		pass
	return files

def get_log_message(location, rev):
	try:
		raw_rev = rev.lstrip("0") or "0"
		with open(os.devnull, "w") as devnull:
			p_log = subprocess.Popen(["svn", "log", "--xml", "-r", raw_rev], cwd=location, stdout=subprocess.PIPE, stderr=devnull)
			xml_out, _ = p_log.communicate()
		if p_log.returncode == 0:
			root = ET.fromstring(xml_out)
			logentry = root.find("logentry")
			if logentry is not None:
				return logentry.findtext("msg") or ""
	except Exception:
		pass
	return ""

def get_rev_list(location, since=None, until=None):
	revs = []
	try:
		with open(os.devnull, "w") as devnull:
			process = subprocess.Popen(["svn", "log", "--xml", "-v", "-r", "1:HEAD"], cwd=location, stdout=subprocess.PIPE, stderr=devnull)
			xml_out, _ = process.communicate()

		if process.returncode != 0:
			return []

		root = ET.fromstring(xml_out)

		for logentry in root.findall("logentry"):
			rev = logentry.attrib["revision"]
			date_element = logentry.findtext("date")
			if date_element:
				dt = datetime.datetime.strptime(date_element.split(".")[0].rstrip("Z"), "%Y-%m-%dT%H:%M:%S")
				commit_date = dt.strftime("%Y-%m-%d")
				if since and commit_date < since:
					continue
				if until and commit_date > until:
					continue

			revs.append(rev)
	except Exception:
		pass

	return revs

def get_log_lines(location, revisions):
	lines = []
	for rev in revisions:
		try:
			raw_rev = rev.lstrip("0") or "0"
			with open(os.devnull, "w") as devnull:
				p_log = subprocess.Popen(["svn", "log", "--xml", "-v", "-r", raw_rev], cwd=location, stdout=subprocess.PIPE, stderr=devnull)
				xml_out, _ = p_log.communicate()

			if p_log.returncode != 0:
				continue

			root = ET.fromstring(xml_out)
			logentry = root.find("logentry")
			if logentry is None:
				continue

			sha = rev.zfill(40)
			author = logentry.findtext("author") or "No Author"
			email = author
			date_element = logentry.findtext("date")

			if date_element:
				dt = datetime.datetime.strptime(date_element.split(".")[0].rstrip("Z"), "%Y-%m-%dT%H:%M:%S")
				timestamp = str(int(calendar.timegm(dt.timetuple())))
				date = dt.strftime("%Y-%m-%d")
			else:
				timestamp = "0"
				date = "1970-01-01"

			commit_line = "\x00".join([timestamp, date, sha, author, email])
			lines.append(commit_line)

			with open(os.devnull, "w") as devnull:
				p_diff = subprocess.Popen(["svn", "diff", "-c", raw_rev], cwd=location, stdout=subprocess.PIPE, stderr=devnull)
				diff_out = decode(p_diff.communicate()[0])

			current_file = None
			insertions = 0
			deletions = 0

			for diff_line in diff_out.splitlines():
				if diff_line.startswith("Index: "):
					if current_file:
						bars = "+" * insertions + "-" * deletions
						if insertions + deletions > 0:
							lines.append(" {0} | {1} {2}".format(current_file, insertions + deletions, bars))
					current_file = diff_line.split("Index: ", 1)[1].strip()
					if os.path.isabs(current_file) and current_file.startswith(location):
						current_file = os.path.relpath(current_file, location)
					insertions = 0
					deletions = 0
				elif diff_line.startswith("+") and not diff_line.startswith("+++"):
					insertions += 1
				elif diff_line.startswith("-") and not diff_line.startswith("---"):
					deletions += 1

			if current_file:
				bars = "+" * insertions + "-" * deletions
				if insertions + deletions > 0:
					lines.append(" {0} | {1} {2}".format(current_file, insertions + deletions, bars))

		except Exception:
			continue

	return lines

def get_blame_porcelain(location, rel_path):
	abs_path = os.path.join(location, rel_path)
	if not os.path.exists(abs_path):
		return []

	try:
		with open(os.devnull, "w") as devnull:
			p_blame = subprocess.Popen(["svn", "blame", "--xml", abs_path], cwd=location, stdout=subprocess.PIPE, stderr=devnull)
			xml_out, _ = p_blame.communicate()

		if p_blame.returncode != 0:
			return []

		root = ET.fromstring(xml_out)

		with open(abs_path, "rb") as f:
			file_lines = f.read().splitlines()

		entries = {}
		target = root.find("target")
		if target is not None:
			for entry in target.findall("entry"):
				line_no = int(entry.attrib["line-number"])
				commit = entry.find("commit")
				if commit is not None:
					rev = commit.attrib.get("revision", "0").zfill(40)
					author = commit.findtext("author") or "No Author"
					date_element = commit.findtext("date")
					if date_element:
						dt = datetime.datetime.strptime(date_element.split(".")[0].rstrip("Z"), "%Y-%m-%dT%H:%M:%S")
						timestamp = int(calendar.timegm(dt.timetuple()))
					else:
						timestamp = 0
					entries[line_no] = (rev, author, timestamp)

		porcelain_lines = []
		for line_no, line_content in enumerate(file_lines, 1):
			if line_no in entries:
				rev, author, timestamp = entries[line_no]
			else:
				rev, author, timestamp = "0".zfill(40), "No Author", 0

			porcelain_lines.append(rev)
			porcelain_lines.append("author {0}".format(author))
			porcelain_lines.append("author-mail <{0}>".format(author))
			porcelain_lines.append("author-time {0}".format(timestamp))
			porcelain_lines.append("filename {0}".format(rel_path))
			porcelain_lines.append(decode(line_content))

		return porcelain_lines
	except Exception:
		return []
