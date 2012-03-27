# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Load test for the Storage server
"""
import os
import base64
import hashlib
import random
import json
import time

from funkload.FunkLoadTestCase import FunkLoadTestCase
from funkload.utils import Data

import macauthlib
from webob import Request
from mozsvc.user.whoauth import SagradaMACAuthPlugin

VERSION = '1.0'
put_count_distribution = [0, 18, 67, 9, 4, 2]  # 0% 0 PUTs, 18% 1 PUT, etc.

# Use the auth plugin to generate fake auth tokens.
# It must be configured to use the same secrets as the server under test.
auth_plugin = SagradaMACAuthPlugin(secret="TED KOPPEL IS A ROBOT")


class StressTest(FunkLoadTestCase):

    def setUp(self):
        nodes = self.conf_get("main", "nodes").split("\n")
        nodes = [node.strip() for node in nodes]
        self.nodes = [node for node in nodes if not node.startswith("#")]

    def setMACAuthHeader(self, method, url, token, secret):
        """Set the Sagrada MAC Auth header using the given credentials."""
        req = Request.blank(url)
        req.method = method
        macauthlib.sign_request(req, token, secret)
        self.clearHeaders()
        self.addHeader("Authorization", req.environ["HTTP_AUTHORIZATION"])

    def test_app_storage_session(self):
        userid = self._pick_user()
        node = self._pick_node()
        self.logd("choosing node %s" % (node))

        # Generate authentication token
        req = Request.blank(node)
        token, secret = auth_plugin.encode_mac_id(req, {"uid": userid})

        # Initial GET of the (empty) set of apps.
        self.setOkCodes([200])
        url = node + "/%s/%s/apps/" % (VERSION, userid)
        self.setMACAuthHeader("GET", url, token, secret)
        response = self.get(url)

        TEST_APP_DATA = {
            "origin": "https://example.com",
            "manifestPath": "/manifest.webapp",
            "installOrigin": "https://marketplace.mozilla.org",
            "modifiedAt": 1234,   # this will be overwritten on write
            "installedAt": 1234,  # this will not be overwritten
            "receipts": ["receipt1", "receipt2"],
        }

        # Alternating series of PUTs and GETs.
        for x in range(self._pick_weighted_count(put_count_distribution)):
            self.setOkCodes([201, 204])
            data = TEST_APP_DATA.copy()
            data["origin"] = "https://example%d.com" % (x,)
            id = hashlib.sha1(data["origin"]).digest()
            id = base64.urlsafe_b64encode(id).rstrip("=")
            url = node + "/%s/%s/apps/%s"
            url = url % (VERSION, userid, id)
            data = Data('application/json', json.dumps(data))
            self.logd("about to PUT (x=%d) %s" % (x, url))
            self.setMACAuthHeader("PUT", url, token, secret)
            response = self.put(url, params=data)

            self.setOkCodes([200])
            url = node + "/%s/%s/apps/" % (VERSION, userid)
            self.setMACAuthHeader("GET", url, token, secret)
            response = self.get(url)

    def _pick_node(self):
        """Randomly select a node on which to store the apps."""
        return random.choice(self.nodes)

    def _pick_user(self):
        """Randomly select a userid for use during storage."""
        return random.randint(1, 1000000)

    def _pick_weighted_count(self, weights):
        target = random.randint(1, sum(weights))
        total = 0
        for i, weight in enumerate(weights):
            total += weight
            if total >= target:
                return i
        assert False, "_pick_weighted_count ran off the end of the list"
