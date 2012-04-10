# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from syncstorage.tests.functional.support import StorageFunctionalTestCase


class AITCFunctionalTestCase(StorageFunctionalTestCase):

    def get_configurator(self):
        config = super(AITCFunctionalTestCase, self).get_configurator()
        config.include("aitc")
        return config
