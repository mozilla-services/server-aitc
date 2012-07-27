# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json

from metlog.senders import DebugCaptureSender

from aitc.views import get_collection
from aitc.tests.support import AITCTestCase


class TestMetlog(AITCTestCase):

    def make_request(self, *args, **kwds):
        req = super(TestMetlog, self).make_request(*args, **kwds)
        req.user = {'uid': 'aa'}
        return req

    def test_sender_class(self):
        sender = self.metlog.sender
        self.assertTrue(isinstance(sender, DebugCaptureSender))

    def test_service_view_wrappers(self):
        req = self.make_request(environ={"HTTP_HOST": "localhost"})
        req.matchdict = {'collection': 'foo'}
        get_collection(req)
        # The two most recent msgs should be from processing that request.
        # There may be more messages due to e.g. warnings at startup.
        msgs = self.metlog.sender.msgs
        self.assertTrue(len(msgs) >= 2)
        timer_msg = json.loads(msgs[-2])
        counter_msg = json.loads(msgs[-1])
        self.assertEqual(timer_msg['type'], 'timer')
        self.assertEqual(timer_msg['fields']['name'],
                         'aitc.views.get_collection')
        self.assertEqual(counter_msg['type'], 'counter')
        self.assertEqual(counter_msg['fields']['name'],
                         'aitc.views.get_collection')
