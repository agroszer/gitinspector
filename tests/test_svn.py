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
import os
import shutil
import tempfile

try:
	import unittest2 as unittest
except ImportError:
	import unittest

from gitinspector import svn
from .harness import SvnRepository, analyze_blame, analyze_changes, analyze_metrics
from .test_options import run_inside

class SvnModuleTest(unittest.TestCase):
	def test_is_available(self):
		self.assertTrue(svn.is_available())

	def test_is_svn_repository(self):
		repo = SvnRepository()
		try:
			self.assertTrue(svn.is_svn_repository(repo.location))
			non_repo = tempfile.mkdtemp(prefix="gitinspector-test-non-svn-")
			try:
				self.assertFalse(svn.is_svn_repository(non_repo))
			finally:
				shutil.rmtree(non_repo)
		finally:
			repo.remove()

class SvnAnalysisTest(unittest.TestCase):
	def setUp(self):
		self.repository = SvnRepository()
		self.repository.commit("Initial commit", {"file1.py": "print('hello')\nline2\n"}, author="Alice")
		self.repository.commit("Second commit", {"file1.py": "print('hello')\nline2\nline3\n", "file2.py": "def foo():\n    pass\n"}, author="Bob")

	def tearDown(self):
		self.repository.remove()

	def test_changes_analysis(self):
		ch = analyze_changes(self.repository)
		commits = ch.get_commits()
		self.assertEqual(len(commits), 2)
		authors = ch.get_authorinfo_list()
		self.assertIn("Alice", authors)
		self.assertIn("Bob", authors)

	def test_blame_analysis(self):
		ch = analyze_changes(self.repository)
		bl = analyze_blame(self.repository, ch)
		summed = bl.get_summed_blames()
		self.assertIn("Alice", summed)
		self.assertIn("Bob", summed)
		self.assertGreater(summed["Alice"].lines, 0)
		self.assertGreater(summed["Bob"].lines, 0)

	def test_metrics_analysis(self):
		metrics = analyze_metrics(self.repository)
		self.assertIsNotNone(metrics)

	def test_gitinspector_cli_run(self):
		status, output, errors = run_inside(self.repository.location, "-F", "json")
		self.assertEqual(status, 0, errors)
		self.assertIn("Alice", output)
		self.assertIn("Bob", output)
