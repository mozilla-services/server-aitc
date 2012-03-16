# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Functional tests for the AITC server protocol.

This file runs tests to ensure the correct operation of the server
as specified in:

    http://docs.services.mozilla.com/aitc/apis-1.0.html

If there's an aspect of that spec that's not covered by a test in this file,
consider it a bug.

"""

import unittest2

import os
import sys
import time
import simplejson as json

from syncstorage.util import get_timestamp

from aitc.records import origin_to_id
from aitc.tests.functional.support import AITCFunctionalTestCase

import macauthlib

from mozsvc.user.whoauth import SagradaMACAuthPlugin


class TestAITC(AITCFunctionalTestCase):
    """AITC testcases that only use the web API.

    These tests are suitable for running against both in-process and live
    external web servers.
    """

    def setUp(self):
        super(TestAITC, self).setUp()

        self.root = "/1.0/" + str(self.user_id)

        # Create a SagradaMACAuthPlugin from our deployment settings,
        # so that we can generate valid authentication tokens.
        settings = self.config.registry.settings
        macauth_settings = settings.getsection("who.plugin.macauth")
        macauth_settings.pop("use", None)
        auth_plugin = SagradaMACAuthPlugin(**macauth_settings)

        # Monkey-patch the app to sign all requests with a macauth token.
        def new_do_request(req, *args, **kwds):
            id, key = auth_plugin.encode_mac_id(req, {"userid": self.user_id})
            macauthlib.sign_request(req, id, key)
            return orig_do_request(req, *args, **kwds)
        orig_do_request = self.app.do_request
        self.app.do_request = new_do_request

        # Reset the storage to a known state (aka "empty").
        for app in self.app.get(self.root + "/apps/").json["apps"]:
            id = origin_to_id(app["origin"])
            self.app.delete(self.root + "/apps/" + id)
        apps = self.app.get(self.root + "/apps/").json["apps"]
        self.assertEquals(apps, [])
        for device in self.app.get(self.root + "/devices/").json["devices"]:
            self.app.delete(self.root + "/devices/" + device["uuid"])
        devices = self.app.get(self.root + "/devices/").json["devices"]
        self.assertEquals(devices, [])
        
    def test_putting_an_app(self):
        # Putting it at the correct URL succeeds.
        data = {
            "origin": "https://example.com",
            "manifestPath": "/manifest.webapp",
            "installOrigin": "https://marketplace.mozilla.org",
            "installedAt": 1330535996745,
            "modifiedAt": 1330535996945,
            "receipts": ["receipt1", "receipt2"],
        }
        id = origin_to_id(data["origin"])
        self.app.put_json(self.root + "/apps/" + id, data)
        apps = self.app.get(self.root + "/apps/").json["apps"]
        self.assertEquals(len(apps), 1)
        # Putting it at an incorrect URL fails.
        id = origin_to_id("https://evil.com")
        self.app.put_json(self.root + "/apps/" + id, data, status=400)
        apps = self.app.get(self.root + "/apps/").json["apps"]
        self.assertEquals(len(apps), 1)
