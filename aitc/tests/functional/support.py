# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import urlparse
import random

from syncstorage.tests.functional.support import StorageFunctionalTestCase


class AITCFunctionalTestCase(StorageFunctionalTestCase):

    def get_test_configurator(self):
        # This misuse of super() is intentional.
        # I want to avoid the StorageFunctionalTestCase itself, so
        # that we don't wind up including the syncstorage app.
        config = super(StorageFunctionalTestCase, self).get_test_configurator()
        config.include("aitc")
        return config
