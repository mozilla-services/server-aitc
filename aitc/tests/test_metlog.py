# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json

from aitc.views import get_collection
from metlog.senders import DebugCaptureSender
from mozsvc.metrics import teardown_metlog
from mozsvc.plugin import load_from_settings
from mozsvc.tests.support import TestCase


class TestMetlog(TestCase):

    def make_request(self, *args, **kwds):
        req = super(TestMetlog, self).make_request(*args, **kwds)
        req.user = {'uid': 'aa'}
        return req

    def tearDown(self):
        teardown_metlog()
        # clear the threadlocal
        self.config.end()
        super(TestMetlog, self).tearDown()

    def get_test_configurator(self):
        config = super(TestMetlog, self).get_test_configurator()
        metlog_wrapper = load_from_settings('metlog', config.registry.settings)
        self.metlog = metlog_wrapper.client
        config.registry['metlog'] = self.metlog
        # put it into the threadlocal
        config.begin()
        config.include("aitc")
        return config

    def test_sender_class(self):
        sender = self.metlog.sender
        self.assertTrue(isinstance(sender, DebugCaptureSender))

    def test_service_view_wrappers(self):
        req = self.make_request(environ={"HTTP_HOST": "localhost"})
        req.matchdict = {'collection': 'foo'}
        get_collection(req)
        msgs = self.metlog.sender.msgs
        self.assertEqual(len(msgs), 2)
        timer_msg = json.loads(msgs[0])
        wsgi_msg = json.loads(msgs[1])
        self.assertEqual(timer_msg['type'], 'timer')
        self.assertEqual(timer_msg['fields']['name'],
                         'aitc.views:get_collection')
        self.assertEqual(wsgi_msg['type'], 'wsgi')
        self.assertEqual(wsgi_msg['fields']['headers'],
                         {'path': '/', 'host': 'localhost',
                          'User-Agent': ''})
