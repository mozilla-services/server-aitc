# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import unittest
import functools
import StringIO
from runpy import run_module

from syncstorage.tests.support import restore_env

import aitc


TEST_INI_FILE = os.path.join(os.path.dirname(__file__), "tests.ini")


class TestsThatOnlyServeToIncreaseLOCCoverage(unittest.TestCase):
    """Suite of miscellanrous tests that increase line coverage.

    These tests don't really test any functionality, they just run
    various frameworky lines of code to check for obvious errors like
    variable name typos.

    Oh yes, and they help increate LOC coverage...
    """

    @restore_env("AITC_TEST_ONE", "AITC_TEST_TWO")
    def test_that_restore_env_actually_works(self):
        @restore_env("AITC_TEST_ONE", "AITC_TEST_TWO")
        def testit():
            os.environ["AITC_TEST_ONE"] = "WRONG"
            os.environ["AITC_TEST_TWO"] = "WRONG"
        os.environ["AITC_TEST_ONE"] = "one"
        self.assertEquals(os.environ.get("AITC_TEST_ONE"), "one")
        self.assertEquals(os.environ.get("AITC_TEST_TWO"), None)
        testit()
        self.assertEquals(os.environ.get("AITC_TEST_ONE"), "one")
        self.assertEquals(os.environ.get("AITC_TEST_TWO"), None)

    def test_that_the_main_function_produces_a_wsgi_app(self):
        app = aitc.main({"__file__": TEST_INI_FILE})
        self.assertTrue(callable(app))

    @restore_env("AITC_INI_FILE")
    def test_that_run_script_produces_an_application(self):
        os.environ["AITC_INI_FILE"] = TEST_INI_FILE
        run_module("aitc.run", run_name="__main__")

    @restore_env("MOZSVC_TEST_REMOTE", "MOZSVC_TEST_INI_FILE")
    def test_that_functional_tests_can_be_run_as_a_script(self):
        module = "aitc.tests.functional.test_aitc"
        orig_argv = sys.argv
        orig_stdout = sys.stdout
        orig_stderr = sys.stderr
        try:
            sys.argv = [sys.argv[0]]
            sys.stdout = StringIO.StringIO()
            sys.stderr = StringIO.StringIO()
            # With no args, that's a usage error.
            try:
                run_module(module, run_name="__main__")
            except (Exception, SystemExit):
                pass
            self.assertTrue("USAGE" in sys.stderr.getvalue())
            # With args, it will run (and fail, but run nonetheless)
            sys.argv.append("http://nonexistant.example.com")
            sys.argv.append(TEST_INI_FILE)
            try:
                run_module(module, run_name="__main__")
            except (Exception, SystemExit):
                pass
        finally:
            sys.stderr = orig_stderr
            sys.stdout = orig_stdout
            sys.argv = orig_argv
