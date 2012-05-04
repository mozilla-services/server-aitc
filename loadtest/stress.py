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
import urlparse
from webtest import TestApp

from ConfigParser import NoOptionError
from funkload.FunkLoadTestCase import FunkLoadTestCase
from funkload.utils import Data

import macauthlib
from webob import Request
from browserid.tests.support import make_assertion
from mozsvc.user.whoauth import SagradaMACAuthPlugin


VERSION = '1.0'
put_count_distribution = [0, 18, 67, 9, 4, 2]  # 0% 0 PUTs, 18% 1 PUT, etc.


from webob import Request

from funkload.utils import Data

from aitc.tests.functional.test_aitc import TestAITC


class AllOKCodes(object):
    """Contain that claims to contain everything.

    This lets us fake out the ok_codes checking inside funkload.
    """

    def __contains__(self, item):
        return True


class FunkLoadWSGIApp(object):
    """WSGI Application that proxies to a FunkLoadTestCase instance."""

    def __init__(self, flobj):
        self.flobj = flobj

    def __call__(self, environ, start_response):
        req = Request(environ)
        flobj = self.flobj
        # Set all headers that won't be set automatically by funkload.
        flobj.clearHeaders()
        for header, value in req.headers.iteritems():
            if header.lower() not in ("host",):
                flobj.setHeader(header, value)
        # Accept any response code, it will be checked by calling code.
        flobj.ok_codes = AllOKCodes()
        resp = flobj.method(req.method, req.url, Data(req.content_type, req.body))
        start_response(str(resp.code) + " " + resp.message, resp.headers.items())
        return (resp.body,)


class StressTest(FunkLoadTestCase, TestAITC):

    def __init__(self, methodName="runTest", *args, **kwds):
        FunkLoadTestCase.__init__(self, methodName, *args, **kwds)
        TestAITC.__init__(self, methodName)

    def setUp(self):
        # Should we use a tokenserver or synthesize our own?
        try:
            self.token_server_url = self.conf_get("main", "token_server_url")
            self.logi("using tokenserver at %s" % (self.token_server_url,))
        except NoOptionError:
            self.token_server_url = None
            secrets_file = self.conf_get("main", "secrets_file")
            self.auth_plugin = SagradaMACAuthPlugin(secrets_file=secrets_file)
            nodes = self.conf_get("main", "endpoint_nodes").split("\n")
            nodes = [node.strip() for node in nodes]
            nodes = [node for node in nodes if not node.startswith("#")]
            self.endpoint_nodes = nodes
            self.logi("using secrets_file from %s" % (secrets_file,))
        FunkLoadTestCase.setUp(self)
        TestAITC.setUp(self)

    def _authenticate(self):
        token, secret, endpoint_url = (s.encode("ascii") for s in self._generate_token())
        self.auth_token = token
        self.auth_secret = secret
        self.endpoint_url = endpoint_url
        self.user_id = int(endpoint_url.strip("/").rsplit("/", 1)[-1])
        host_url = urlparse.urlparse(endpoint_url)
        self.app = TestApp(FunkLoadWSGIApp(self), extra_environ={
            "HTTP_HOST": host_url.netloc,
            "wsgi.url_scheme": host_url.scheme or "http",
            "SERVER_NAME": host_url.hostname,
            "REMOTE_ADDR": "127.0.0.1",
        })

    def setMACAuthHeader(self, method, url, token, secret):
        """Set the Sagrada MAC Auth header using the given credentials."""
        req = Request.blank(url)
        req.method = method
        macauthlib.sign_request(req, token, secret)
        self.clearHeaders()
        self.addHeader("Authorization", req.environ["HTTP_AUTHORIZATION"])

    def method(self, *args, **kwds):
        self.logi("REQUEST: " + str(args) + "  " + str(kwds))
        try:
            response = super(StressTest, self).method(*args, **kwds)
        except Exception, e:
            self.logi("    ERROR: " + str(e))
            raise
        else:
            self.logi("    RESPONSE: " + str(response))
            self.logi("              " + str(response.body))
            return response

    def test_app_storage_session(self):
        # Initial GET of the (empty) set of apps.
        self.setOkCodes([200])
        url = self.endpoint_url + "/apps/"
        self.setMACAuthHeader("GET", url, self.auth_token, self.auth_secret)
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
            url = self.endpoint_url + "/apps/" + id
            data = Data('application/json', json.dumps(data))
            self.logi("about to PUT (x=%d) %s" % (x, url))
            self.setMACAuthHeader("PUT", url, self.auth_token, self.auth_secret)
            response = self.put(url, params=data)

            self.setOkCodes([200])
            url = self.endpoint_url + "/apps/"
            self.setMACAuthHeader("GET", url, self.auth_token, self.auth_secret)
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
        uid = random.randint(1, 950)
        # Use the tokenserver if configured, otherwise fake it ourselves.
        if self.token_server_url is None:
            self.logi("synthesizing token for uid %s" % (uid,))
            endpoint_node = random.choice(self.endpoint_nodes)
            req = Request.blank(endpoint_node)
            token, secret = self.auth_plugin.encode_mac_id(req, {"uid": uid})
            endpoint_url = endpoint_node + "/%s/%s" % (VERSION, uid)
        else:
            email = "user_%s@loadtest.local" % (uid,)
            self.logi("requesting token for %s" % (email,))
            assertion = make_assertion(email, audience="https://persona.org",
                                       issuer="loadtest.local")
            token_url = self.token_server_url + "/1.0/aitc/1.0"
            self.addHeader("Authorization", "Browser-ID " + assertion)
            response = self.get(token_url)
            self.logi(response.body)
            credentials = json.loads(response.body)
            token = credentials["id"].encode("ascii")
            secret = credentials["key"].encode("ascii")
            endpoint_url = credentials["api_endpoint"]

        self.logi("assigned endpoint_url %s" % (endpoint_url))
        return token, secret, endpoint_url

