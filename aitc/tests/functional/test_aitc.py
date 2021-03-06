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
import webtest

from mozsvc.exceptions import BackendError

from syncstorage.tests.support import restore_env
from syncstorage.tests.functional.support import run_live_functional_tests

from aitc.records import origin_to_id
from aitc.tests.functional.support import AITCFunctionalTestCase


TEST_APP_DATA = {
    "origin": "https://example.com",
    "manifestPath": "/manifest.webapp",
    "installOrigin": "https://marketplace.mozilla.org",
    "name": "Examplinator 3000",
    "receipts": ["receipt1", "receipt2"],
}

TEST_DEVICE_DATA = {
    "uuid": "75B538D8-67AF-44E8-86A0-B1A07BE137C8",
    "name": "Anant's Mac Pro",
    "type": "mobile",
    "layout": "android/phone",
    "apps": {"foo": "bar"},
}


class TestAITC(AITCFunctionalTestCase):
    """AITC testcases that only use the web API.

    These tests are suitable for running against both in-process and live
    external web servers.
    """

    def setUp(self):
        super(TestAITC, self).setUp()

        self.root = "/1.0/" + str(self.user_id)

        # Reset the storage to a known state (aka "empty").
        apps = self.app.get(self.root + "/apps/").json["apps"]
        for app in apps:   # pragma: nocover
            id = origin_to_id(app["origin"])
            self.app.delete(self.root + "/apps/" + id)
        apps = self.app.get(self.root + "/apps/").json["apps"]
        self.assertEquals(apps, [])
        devices = self.app.get(self.root + "/devices/").json["devices"]
        for device in devices:  # pragma: nocover
            id = device["uuid"].encode("ascii")
            self.app.delete(self.root + "/devices/" + id)
        devices = self.app.get(self.root + "/devices/").json["devices"]
        self.assertEquals(devices, [])

    def test_that_only_defined_collection_names_are_available(self):
        # SyncStorage creates collections on first read, so this fails.
        #self.app.get(self.root + "/foo", status=404)
        #self.app.get(self.root + "/foo/", status=404)
        pass

    def test_that_syncstorage_urls_do_not_leak_through(self):
        self.app.get(self.root + "/info/collections", status=404)
        self.app.get(self.root + "/storage/apps", status=404)

    def test_storing_and_retrieving_an_app(self):
        # Putting it at the correct URL succeeds.
        data = TEST_APP_DATA.copy()
        id = origin_to_id(data["origin"])
        self.app.put_json(self.root + "/apps/" + id, data)
        apps = self.app.get(self.root + "/apps/").json["apps"]
        self.assertEquals(len(apps), 1)
        self.assertEquals(apps[0]["origin"], data["origin"])
        # Putting it at an incorrect URL fails.
        id = origin_to_id("https://evil.com")
        self.app.put_json(self.root + "/apps/" + id, data, status=403)
        apps = self.app.get(self.root + "/apps/").json["apps"]
        self.assertEquals(len(apps), 1)
        # Reading it back gives us the correct information.
        id = origin_to_id(data["origin"])
        app1 = self.app.get(self.root + "/apps/" + id).json
        self.assertEquals(app1["origin"], data["origin"])
        # Writing it again updates the modified time.
        time.sleep(0.01)
        self.app.put_json(self.root + "/apps/" + id, data)
        app2 = self.app.get(self.root + "/apps/" + id).json
        self.assertEquals(app2["origin"], data["origin"])
        self.assertEquals(app2["installedAt"], app1["installedAt"])
        self.assertGreater(app2["modifiedAt"], app1["modifiedAt"])
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
        self.assertEquals(devices[0]["uuid"], data["uuid"])
        # Putting it at an incorrect URL fails.
        bad_id = "8" + data["uuid"][1:]
        self.app.put_json(self.root + "/devices/" + bad_id, data, status=403)
        devices = self.app.get(self.root + "/devices/").json["devices"]
        self.assertEquals(len(devices), 1)
        # Reading it back gives us the correct information.
        device1 = self.app.get(self.root + "/devices/" + data["uuid"]).json
        self.assertEquals(device1["uuid"], data["uuid"])
        self.assertEquals(device1["layout"], data["layout"])
        # Writing it again updates the modified time.
        time.sleep(0.01)
        self.app.put_json(self.root + "/devices/" + data["uuid"], data)
        device2 = self.app.get(self.root + "/devices/" + data["uuid"]).json
        self.assertEquals(device2["uuid"], data["uuid"])
        self.assertEquals(device2["layout"], data["layout"])
        self.assertEquals(device2["addedAt"], device1["addedAt"])
        self.assertGreater(device2["modifiedAt"], device1["modifiedAt"])
        # Deleting it makes it go away.
        self.app.delete(self.root + "/devices/" + data["uuid"], status=204)
        devices = self.app.get(self.root + "/devices/").json["devices"]
        self.assertEquals(len(devices), 0)

    def test_that_app_timestamp_fields_are_set_on_write(self):
        data = TEST_APP_DATA.copy()
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
        ts1 = int(r.headers["X-Last-Modified"])
        time.sleep(0.01)
        data2 = TEST_APP_DATA.copy()
        data2["origin"] = "http://testapp.com"
        id2 = origin_to_id(data2["origin"])
        r = self.app.put_json(self.root + "/apps/" + id2, data2)
        ts2 = int(r.headers["X-Last-Modified"])
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

    def test_listing_of_full_app_records(self):
        data1 = TEST_APP_DATA.copy()
        id1 = origin_to_id(data1["origin"])
        self.app.put_json(self.root + "/apps/" + id1, data1)
        data2 = TEST_APP_DATA.copy()
        data2["origin"] = "http://testapp.com"
        id2 = origin_to_id(data2["origin"])
        self.app.put_json(self.root + "/apps/" + id2, data2)
        # Without "full" we get the abbreviated form.
        apps = self.app.get(self.root + "/apps/").json["apps"]
        self.assertEquals(len(apps), 2)
        for app in apps:
            self.assertEquals(sorted(app.keys()), ["modifiedAt", "origin"])
        # With "full" we get the full data output.
        apps = self.app.get(self.root + "/apps/?full=1").json["apps"]
        self.assertEquals(len(apps), 2)
        # Sort the apps and output by origin so we easily compare in a loop.
        apps = [(app["origin"], app) for app in apps]
        apps = [app for (origin, app) in sorted(apps)]
        # Make sure we got *all* the data back correctly.
        for app, data in zip(apps, [data2, data1]):
            del app["modifiedAt"]
            del app["installedAt"]
            self.assertEquals(app, data)

    def test_listing_of_apps_with_x_if_modified_since(self):
        data1 = TEST_APP_DATA.copy()
        id1 = origin_to_id(data1["origin"])
        r = self.app.put_json(self.root + "/apps/" + id1, data1)
        ts1 = int(r.headers["X-Last-Modified"])
        time.sleep(0.01)
        # No X-I-M-S header => full listing.
        apps = self.app.get(self.root + "/apps/", status=200)
        self.assertEquals(len(apps.json["apps"]), 1)
        # X-I-M-S header some time before the write => full listing.
        headers = {"X-If-Modified-Since": str(ts1 - 1)}
        apps = self.app.get(self.root + "/apps/", headers=headers, status=200)
        self.assertEquals(len(apps.json["apps"]), 1)
        # X-I-M-S header equals time of write => 304 Not Modified
        headers = {"X-If-Modified-Since": str(ts1)}
        self.app.get(self.root + "/apps/", headers=headers, status=304)
        # X-I-M-S header some time after the write => 304 Not Modified
        headers = {"X-If-Modified-Since": str(ts1 + 1)}
        self.app.get(self.root + "/apps/", headers=headers, status=304)
        # Modify it, then we get the full listing again.
        data2 = TEST_APP_DATA.copy()
        data2["origin"] = "http://testapp.com"
        id2 = origin_to_id(data2["origin"])
        r = self.app.put_json(self.root + "/apps/" + id2, data2)
        ts2 = int(r.headers["X-Last-Modified"])
        time.sleep(0.01)
        headers = {"X-If-Modified-Since": str(ts1 + 1)}
        apps = self.app.get(self.root + "/apps/", headers=headers, status=200)
        self.assertEquals(len(apps.json["apps"]), 2)
        # Using updated timestamp gives 304 again.
        headers = {"X-If-Modified-Since": str(ts2 + 1)}
        self.app.get(self.root + "/apps/", headers=headers, status=304)
        # But if we *delete* an app, that counts as being modified.
        # XXX TODO: this behaviour currently only works with memcached backend.
        # It's considered a "non-essential behaviour" in that the current
        # client software should work OK without it.  Hence, disabling test.
        #self.app.delete(self.root + "/apps/" + id1)
        #headers = {"X-If-Modified-Since": str(ts2 + 1)}
        #apps = self.app.get(self.root + "/apps/", headers=headers, status=200)
        #self.assertEquals(len(apps.json["apps"]), 1)

    def test_getting_an_app_with_x_if_modified_since(self):
        data = TEST_APP_DATA.copy()
        id = origin_to_id(data["origin"])
        r = self.app.put_json(self.root + "/apps/" + id, data)
        ts = int(r.headers["X-Last-Modified"])
        time.sleep(0.01)
        # No X-I-M-S header => we get the app data.
        app = self.app.get(self.root + "/apps/" + id).json
        del app["modifiedAt"]
        del app["installedAt"]
        self.assertEquals(app, data)
        # X-I-M-S header before time of write => we get the app data.
        headers = {"X-If-Modified-Since": str(ts - 1)}
        app = self.app.get(self.root + "/apps/" + id).json
        del app["modifiedAt"]
        del app["installedAt"]
        self.assertEquals(app, data)
        # X-I-M-S header at time of write => 304 Not Modified
        headers = {"X-If-Modified-Since": str(ts)}
        self.app.get(self.root + "/apps/" + id, headers=headers, status=304)
        # X-I-M-S header after time of write => 304 Not Modified
        headers = {"X-If-Modified-Since": str(ts + 1)}
        self.app.get(self.root + "/apps/" + id, headers=headers, status=304)
        # After another write, we get the updated data.
        self.app.put_json(self.root + "/apps/" + id, data)
        headers = {"X-If-Modified-Since": str(ts + 1)}
        app = self.app.get(self.root + "/apps/" + id, headers=headers).json
        del app["modifiedAt"]
        del app["installedAt"]
        self.assertEquals(app, data)

    def test_putting_an_app_with_x_if_unmodified_since(self):
        data = TEST_APP_DATA.copy()
        id = origin_to_id(data["origin"])
        # The first put should give a 201 Created.
        r = self.app.put_json(self.root + "/apps/" + id, data, status=201)
        # No X-I-U-S header => we can put an update.
        # The second write gives a 204 No Content.
        r = self.app.put_json(self.root + "/apps/" + id, data, status=204)
        ts = int(r.headers["X-Last-Modified"])
        time.sleep(0.01)
        # X-I-U-S header before time of write => 412 Precondition Failed
        headers = {"X-If-Unmodified-Since": str(ts - 1)}
        self.app.put_json(self.root + "/apps/" + id, data, headers=headers,
                          status=412)
        # X-I-U-S header at time of write => update succeeds
        headers = {"X-If-Unmodified-Since": str(ts)}
        r = self.app.put_json(self.root + "/apps/" + id, data, headers=headers,
                              status=204)
        ts = int(r.headers["X-Last-Modified"])
        time.sleep(0.01)
        # X-I-U-S header after time of write => update succeeds.
        headers = {"X-If-Unmodified-Since": str(ts + 1)}
        self.app.put_json(self.root + "/apps/" + id, data, headers=headers,
                          status=204)

    def test_creating_an_app_with_x_if_unmodified_since_equal_to_zero(self):
        data = TEST_APP_DATA.copy()
        id = origin_to_id(data["origin"])
        headers = {"X-If-Unmodified-Since": "0"}
        # The first put should give a 201 Created.
        self.app.put_json(self.root + "/apps/" + id, data, headers=headers,
                          status=201)
        # The second put fails due to conflict.
        self.app.put_json(self.root + "/apps/" + id, data, headers=headers,
                          status=412)

    def test_that_app_upload_size_is_limited_to_eight_kilobytes(self):
        data = TEST_APP_DATA.copy()
        id = origin_to_id(data["origin"])
        # Fails with >8KB of data
        data["receipts"] = ["X" * 8 * 1024]
        self.app.put_json(self.root + "/apps/" + id, data, status=413)
        # Succeeds with <8KB of data
        data["receipts"] = ["X" * 7 * 1024]
        self.app.put_json(self.root + "/apps/" + id, data, status=201)

    def test_that_device_upload_size_is_limited_to_eight_kilobytes(self):
        data = TEST_DEVICE_DATA.copy()
        id = data["uuid"]
        # Fails with >8KB of data
        data["apps"] = {"data": "X" * 8 * 1024}
        self.app.put_json(self.root + "/devices/" + id, data, status=413)
        # Succeeds with <8KB of data
        data["apps"] = {"data": "X" * 7 * 1024}
        self.app.put_json(self.root + "/devices/" + id, data, status=201)

    def test_deleting_an_app_with_x_if_unmodified_since(self):
        data = TEST_APP_DATA.copy()
        id = origin_to_id(data["origin"])
        r = self.app.put_json(self.root + "/apps/" + id, data, status=201)
        ts = int(r.headers["X-Last-Modified"])
        time.sleep(0.01)
        # X-I-U-S header equalt to zero => 412 Precondition Failed
        headers = {"X-If-Unmodified-Since": "0"}
        self.app.delete(self.root + "/apps/" + id, headers=headers, status=412)
        # X-I-U-S header before time of write => 412 Precondition Failed
        headers = {"X-If-Unmodified-Since": str(ts - 1)}
        self.app.delete(self.root + "/apps/" + id, headers=headers, status=412)
        # X-I-U-S header at time of write => delete succeeds
        headers = {"X-If-Unmodified-Since": str(ts)}
        self.app.delete(self.root + "/apps/" + id, headers=headers, status=204)

    def test_that_getting_a_nonexistant_app_gives_a_404_response(self):
        self.app.get(self.root + "/apps/NONEXISTENT", status=404)

    def test_that_deleting_a_nonexistant_app_gives_a_404_response(self):
        self.app.delete(self.root + "/apps/NONEXISTENT", status=404)

    def test_that_uploading_invalid_json_gives_a_400_response(self):
        # Test that it fails for a variety of non-json-object inputs.
        id = origin_to_id("http://broken-app.com")
        data = "NOT JSON"
        self.app.put(self.root + "/apps/" + id, data, status=415)
        data = 42
        self.app.put_json(self.root + "/apps/" + id, data, status=400)
        data = ["NOT", "AN", "OBJECT"]
        self.app.put_json(self.root + "/apps/" + id, data, status=400)
        # Test that is fails for a variety of malformed inputs.
        id = origin_to_id(TEST_APP_DATA["origin"])
        # Fails with an additional, invalid field.
        data = TEST_APP_DATA.copy()
        data["invalid"] = "field"
        self.app.put_json(self.root + "/apps/" + id, data, status=400)
        # Fails with a missing required field.
        data = TEST_APP_DATA.copy()
        data.pop("manifestPath")
        self.app.put_json(self.root + "/apps/" + id, data, status=400)

    def test_that_uploads_to_unknown_collection_give_a_404_response(self):
        data = TEST_APP_DATA.copy()
        id = origin_to_id(data["origin"])
        self.app.put_json(self.root + "/oops/" + id, data, status=404)


class TestAITCMemcached(TestAITC):
    """AITC testcases run against the memcached backend, if available."""

    @restore_env("MOZSVC_TEST_INI_FILE")
    def setUp(self):
        # Force use of the memcached-specific config file.
        # If we can't initialize due to an ImportError or BackendError,
        # assume that memcache is down and skip the test.
        os.environ["MOZSVC_TEST_INI_FILE"] = "tests-memcached.ini"
        try:
            super(TestAITCMemcached, self).setUp()
            # Check that it's actualy usable
            storage = self.config.registry.get("syncstorage:storage:default")
            storage.cache.get("test")
        except (ImportError, BackendError):
            raise unittest2.SkipTest()
        except webtest.AppError, e:
            if "503" not in str(e):
                raise
            raise unittest2.SkipTest()

    def _cleanup_test_databases(self):
        storage = self.config.registry.get("syncstorage:storage:default")
        if storage:
            storage.cache.flush_all()
        super(TestAITCMemcached, self)._cleanup_test_databases()


if __name__ == "__main__":
    # When run as a script, this file will execute the
    # functional tests against a live webserver.
    res = run_live_functional_tests(TestAITC, sys.argv)
    sys.exit(res)
