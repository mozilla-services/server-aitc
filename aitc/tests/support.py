# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from syncstorage.tests.support import StorageTestCase


class AITCTestCase(StorageTestCase):

    def get_configurator(self):
        config = super(AITCTestCase, self).get_configurator()
        config.include("aitc")
        return config
