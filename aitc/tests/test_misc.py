# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import os

import aitc


class TestsThatOnlyServeToIncreaseLOCCoverage(unittest.TestCase):
    """Suite of miscellanrous tests that increase line coverage.

    These tests don't really test any functionality, they just run
    various frameworky lines of code to check for obvious errors like
    variable name typos.

    Oh yes, and they help increate LOC coverage...
    """

    def test_that_the_main_function_produces_a_wsgi_app(self):
        ini_file = os.path.join(os.path.dirname(__file__), "tests.ini")
        app = aitc.main({"__file__": ini_file})
        self.assertTrue(callable(app))
