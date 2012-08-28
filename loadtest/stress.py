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

from ConfigParser import NoOptionError
from funkload.FunkLoadTestCase import FunkLoadTestCase
from funkload.utils import Data

import macauthlib
from webob import Request
from browserid.tests.support import make_assertion
from mozsvc.user import SagradaAuthenticationPolicy


VERSION = '1.0'
put_count_distribution = [0, 18, 67, 9, 4, 2]  # 0% 0 PUTs, 18% 1 PUT, etc.


class StressTest(FunkLoadTestCase):

    def setUp(self):
        # Should we use a tokenserver or synthesize our own?
        try:
            self.token_server_url = self.conf_get("main", "token_server_url")
            self.logi("using tokenserver at %s" % (self.token_server_url,))
        except NoOptionError:
            self.token_server_url = None
            secrets_file = self.conf_get("main", "secrets_file")
            self.auth_plugin = SagradaAuthenticationPolicy(secrets_file=secrets_file)
            nodes = self.conf_get("main", "endpoint_nodes").split("\n")
            nodes = [node.strip() for node in nodes]
            nodes = [node for node in nodes if not node.startswith("#")]
            self.endpoint_nodes = nodes
            self.logi("using secrets_file from %s" % (secrets_file,))

    def setMACAuthHeader(self, method, url, token, secret):
        """Set the Sagrada MAC Auth header using the given credentials."""
        req = Request.blank(url)
        req.method = method
        macauthlib.sign_request(req, token, secret)
        self.clearHeaders()
        self.addHeader("Authorization", req.environ["HTTP_AUTHORIZATION"])

    def get(self, url, *args, **kwds):
        self.logi("GET: " + url)
        try:
            result = super(StressTest, self).get(url, *args, **kwds)
        except Exception, e:
            self.logi("    FAIL: " + str(e))
            raise
        else:
            self.logi("    OK: " + str(result))
            return result

    def put(self, url, *args, **kwds):
        self.logi("PUT: " + url)
        try:
            result = super(StressTest, self).put(url, *args, **kwds)
        except Exception, e:
            self.logi("    FAIL: " + str(e))
            raise
        else:
            self.logi("    OK: " + str(result))
            return result

    def test_app_storage_session(self):
        token, secret, endpoint_url = self._generate_token()

        # Initial GET of the (empty) set of apps.
        self.setOkCodes([200])
        url = endpoint_url + "/apps/"
        self.setMACAuthHeader("GET", url, token, secret)
        response = self.get(url)
        # The list of apps may not be empty, if we happen to be usinga a uid
        # that has already been used.  Just sanity-check that it parses.
        apps = json.loads(response.body)["apps"]

        TEST_APP_DATA = {
            "origin": "https://example.com",
            "manifestPath": "/manifest.webapp",
            "installOrigin": "https://marketplace.mozilla.org",
            "modifiedAt": 1234,   # this will be overwritten on write
            "installedAt": 1234,  # this will not be overwritten
            "name": "Examplinator 3000",
            "receipts": ["receipt1", "receipt2"],
        }

        # Alternating series of PUTs and GETs.
        for x in range(self._pick_weighted_count(put_count_distribution)):
            self.setOkCodes([201, 204])
            data = TEST_APP_DATA.copy()
            data["origin"] = origin = "https://example%d.com" % (x,)
            id = hashlib.sha1(data["origin"]).digest()
            id = base64.urlsafe_b64encode(id).rstrip("=")
            url = endpoint_url + "/apps/" + id
            data = Data('application/json', json.dumps(data))
            self.logi("about to PUT (x=%d) %s" % (x, url))
            self.setMACAuthHeader("PUT", url, token, secret)
            response = self.put(url, params=data)

            self.setOkCodes([200])
            url = endpoint_url + "/apps/"
            self.setMACAuthHeader("GET", url, token, secret)
            response = self.get(url)
            # Make sure that the app we just uploaded is included
            # in the list of apps.
            apps = json.loads(response.body)["apps"]
            for app in apps:
                if app["origin"] == origin:
                    break
            else:
                assert False, "uploaded app was not included in list"

    def _pick_weighted_count(self, weights):
        target = random.randint(1, sum(weights))
        total = 0
        for i, weight in enumerate(weights):
            total += weight
            if total >= target:
                return i
        assert False, "_pick_weighted_count ran off the end of the list"

    def _generate_token(self):
        """Pick an identity, log in and generate the auth token."""
        uid = random.randint(1, 1000000)  # existing user
        # Use the tokenserver if configured, otherwise fake it ourselves.
        if self.token_server_url is None:
            self.logi("synthesizing token for uid %s" % (uid,))
            endpoint_node = random.choice(self.endpoint_nodes)
            req = Request.blank(endpoint_node)
            token, secret = self.auth_plugin.encode_mac_id(req, uid)
            endpoint_url = endpoint_node + "/%s/%s" % (VERSION, uid)
        else:
            email = "user%s@loadtest.local" % (uid,)
            self.logi("requesting token for %s" % (email,))
            assertion = make_assertion(email, audience="persona.org",
                                       issuer="loadtest.local")
            token_url = self.token_server_url + "/1.0/aitc/1.0"
            self.addHeader("Authorization", "Browser-ID " + assertion)
            response = self.get(token_url)
            credentials = json.loads(response.body)
            token = credentials["id"].encode("ascii")
            secret = credentials["key"].encode("ascii")
            endpoint_url = credentials["api_endpoint"]

        self.logi("assigned endpoint_url %s" % (endpoint_url))
        return token, secret, endpoint_url

