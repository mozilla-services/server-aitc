# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from syncstorage.tests.functional.support import StorageFunctionalTestCase

from aitc.tests.support import AITCTestCase


class AITCFunctionalTestCase(StorageFunctionalTestCase, AITCTestCase):
    # There's nothing else to do here.
    # We just want to mix in the updated get_configurator from AITCTestCase.
    pass
