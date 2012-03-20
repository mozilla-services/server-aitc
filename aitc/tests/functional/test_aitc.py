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

from aitc.records import origin_to_id
from aitc.tests.functional.support import AITCFunctionalTestCase

import macauthlib

from mozsvc.user.whoauth import SagradaMACAuthPlugin


TEST_APP_DATA = {
    "origin": "https://example.com",
    "manifestPath": "/manifest.webapp",
    "installOrigin": "https://marketplace.mozilla.org",
    "modifiedAt": 1234,   # this will be overwritten on write
    "installedAt": 1234,  # this will not be overwritten
    "receipts": ["receipt1", "receipt2"],
}

TEST_DEVICE_DATA = {
    "uuid": "75B538D8-67AF-44E8-86A0-B1A07BE137C8",
    "name": "Anant's Mac Pro",
    "type": "mobile",
    "layout": "android/phone",
    "modifiedAt": 1234,  # this will be overwritten on write
    "addedAt": 1234,     # this will not be overwritten
    "apps": {"foo": "bar"}
}


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
        apps = self.app.get(self.root + "/apps/").json["apps"]
        for app in apps:   # pragma: nocover
            id = origin_to_id(app["origin"])
            self.app.delete(self.root + "/apps/" + id)
        apps = self.app.get(self.root + "/apps/").json["apps"]
        self.assertEquals(apps, [])
        devices = self.app.get(self.root + "/devices/").json["devices"]
        for device in devices:  # pragma: nocover
            self.app.delete(self.root + "/devices/" + device["uuid"])
        devices = self.app.get(self.root + "/devices/").json["devices"]
        self.assertEquals(devices, [])

    def test_storing_and_retrieving_an_app(self):
        # Putting it at the correct URL succeeds.
        data = TEST_APP_DATA.copy()
        id = origin_to_id(data["origin"])
        self.app.put_json(self.root + "/apps/" + id, data)
        apps = self.app.get(self.root + "/apps/").json["apps"]
        self.assertEquals(len(apps), 1)
        # Putting it at an incorrect URL fails.
        id = origin_to_id("https://evil.com")
        self.app.put_json(self.root + "/apps/" + id, data, status=400)
        apps = self.app.get(self.root + "/apps/").json["apps"]
        self.assertEquals(len(apps), 1)
        # Reading it back gives us the correct information.
        id = origin_to_id(data["origin"])
        app = self.app.get(self.root + "/apps/" + id).json
        self.assertEquals(app["origin"], data["origin"])
        self.assertEquals(app["installedAt"], data["installedAt"])
        self.assertGreater(app["modifiedAt"], data["modifiedAt"])
        # Deleting it makes it go away.
        self.app.delete(self.root + "/apps/" + id, status=204)
        apps = self.app.get(self.root + "/apps/").json["apps"]
        self.assertEquals(len(apps), 0)

    def test_storing_and_retrieving_a_device(self):
        # Putting it at the correct URL succeeds.
        data = TEST_DEVICE_DATA.copy()
        self.app.put_json(self.root + "/devices/" + data["uuid"], data)
        devices = self.app.get(self.root + "/devices/").json["devices"]
        self.assertEquals(len(devices), 1)
        # Putting it at an incorrect URL fails.
        bad_id = "8" + data["uuid"][1:]
        self.app.put_json(self.root + "/devices/" + bad_id, data, status=400)
        devices = self.app.get(self.root + "/devices/").json["devices"]
        self.assertEquals(len(devices), 1)
        # Reading it back gives us the correct information.
        device = self.app.get(self.root + "/devices/" + data["uuid"]).json
        self.assertEquals(device["uuid"], data["uuid"])
        self.assertEquals(device["layout"], data["layout"])
        self.assertEquals(device["addedAt"], data["addedAt"])
        self.assertGreater(device["modifiedAt"], data["modifiedAt"])
        # Deleting it makes it go away.
        self.app.delete(self.root + "/devices/" + data["uuid"], status=204)
        devices = self.app.get(self.root + "/devices/").json["devices"]
        self.assertEquals(len(devices), 0)

    def test_that_app_timestamp_fields_are_set_on_write(self):
        data = TEST_APP_DATA.copy()
        del data["installedAt"]
        del data["modifiedAt"]
        id = origin_to_id(data["origin"])
        # On first write, both timestamp fields are set to same value.
        self.app.put_json(self.root + "/apps/" + id, data)
        app1 = self.app.get(self.root + "/apps/" + id).json
        self.assertEquals(app1["installedAt"], app1["modifiedAt"])
        # On subsequent writes, only the modified timestamp is set.
        self.app.put_json(self.root + "/apps/" + id, app1)
        app2 = self.app.get(self.root + "/apps/" + id).json
        self.assertEquals(app1["installedAt"], app2["installedAt"])
        self.assertGreater(app2["modifiedAt"], app2["installedAt"])

    def test_that_device_timestamp_fields_are_set_on_write(self):
        data = TEST_DEVICE_DATA.copy()
        del data["addedAt"]
        del data["modifiedAt"]
        id = data["uuid"]
        # On first write, both timestamp fields are set to same value.
        self.app.put_json(self.root + "/devices/" + id, data)
        device1 = self.app.get(self.root + "/devices/" + id).json
        self.assertEquals(device1["addedAt"], device1["modifiedAt"])
        # On subsequent writes, only the modified timestamp is set.
        self.app.put_json(self.root + "/devices/" + id, device1)
        device2 = self.app.get(self.root + "/devices/" + id).json
        self.assertEquals(device1["addedAt"], device2["addedAt"])
        self.assertGreater(device2["modifiedAt"], device2["addedAt"])

    def test_listing_of_apps_modified_after_a_given_time(self):
        # Write two apps, separated by a 10ms sleep.
        data1 = TEST_APP_DATA.copy()
        id1 = origin_to_id(data1["origin"])
        r = self.app.put_json(self.root + "/apps/" + id1, data1)
        ts1 = int(r.headers["X-Timestamp"])
        time.sleep(0.01)
        data2 = TEST_APP_DATA.copy()
        data2["origin"] = "http://testapp.com"
        id2 = origin_to_id(data2["origin"])
	r = self.app.put_json(self.root + "/apps/" + id2, data2)
        ts2 = int(r.headers["X-Timestamp"])
        # With no "after" qualifier", both apps are listed.
        apps = self.app.get(self.root + "/apps/")
        self.assertEquals(len(apps.json["apps"]), 2)
        # With "after" = timestamp of first, we only get one.
        apps = self.app.get(self.root + "/apps/?after=" + str(ts1))
        self.assertEquals(len(apps.json["apps"]), 1)
        self.assertEquals(apps.json["apps"][0]["origin"], data2["origin"])
        # With "after" = just after timestamp of first, we only get one.
        apps = self.app.get(self.root + "/apps/?after=" + str(ts1 + 1))
        self.assertEquals(len(apps.json["apps"]), 1)
        self.assertEquals(apps.json["apps"][0]["origin"], data2["origin"])
        # With "after" = timestamp of second, we get niether
        apps = self.app.get(self.root + "/apps/?after=" + str(ts2))
        self.assertEquals(len(apps.json["apps"]), 0)
        # With "after" = just after timestamp of second, we get niether
        apps = self.app.get(self.root + "/apps/?after=" + str(ts2 + 1))
        self.assertEquals(len(apps.json["apps"]), 0)

    def test_that_uploading_invalid_json_gives_a_400_response(self):
        data = "NOT JSON"
        self.app.put(self.root + "/apps/TESTAPP", data, status=400)
        data = 42
        self.app.put_json(self.root + "/apps/TESTAPP", data, status=400)
        data = ["NOT", "AN", "OBJECT"]
        self.app.put_json(self.root + "/apps/TESTAPP", data, status=400)
        data = {"invalid": "field"}
        self.app.put_json(self.root + "/apps/TESTAPP", data, status=400)
        data = TEST_APP_DATA.copy()
        data.pop("manifestPath")
        self.app.put_json(self.root + "/apps/TESTAPP", data, status=400)

    def test_that_uploads_to_unknown_collection_give_a_404_response(self):
        data = TEST_APP_DATA.copy()
        self.app.put_json(self.root + "/oops/TESTAPP", data, status=404)


if __name__ == "__main__":
    # When run as a script, this file will execute the
    # functional tests against a live webserver.

    if not 2 <= len(sys.argv) <= 3:
        print>>sys.stderr, "USAGE: test_aitc.py <server-url> [<ini-file>]"
        sys.exit(1)

    os.environ["MOZSVC_TEST_REMOTE"] = sys.argv[1]
    if len(sys.argv) > 2:
        os.environ["MOZSVC_TEST_INI_FILE"] = sys.argv[2]

    suite = unittest2.TestSuite()
    suite.addTest(unittest2.makeSuite(TestAITC))
    res = unittest2.TextTestRunner(stream=sys.stderr).run(suite)
    sys.exit(res)
