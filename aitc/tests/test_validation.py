# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import unittest

from aitc.records import AppRecord, DeviceRecord


class TestRecordHandling(unittest.TestCase):

    def test_that_unknown_fields_are_rejected(self):
        self.assertRaises(ValueError, AppRecord, {'boooo': ''})
        self.assertRaises(ValueError, AppRecord, {42: '17'})
        AppRecord({'boooo': ''}, ignore_unknown_fields=True)
        AppRecord({42: '17'}, ignore_unknown_fields=True)
        self.assertRaises(ValueError, DeviceRecord, {'boooo': ''})
        self.assertRaises(ValueError, DeviceRecord, {42: '17'})
        DeviceRecord({'boooo': ''}, ignore_unknown_fields=True)
        DeviceRecord({42: '17'}, ignore_unknown_fields=True)

    def test_validation_of_app_records(self):
        app = AppRecord()
        ok, error = app.validate()
        self.assertFalse(ok)

        good_data = {
            "origin": "https://example.com",
            "manifestPath": "/manifest.webapp",
            "installOrigin": "https://marketplace.mozilla.org",
            "installedAt": 1330535996745,
            "modifiedAt": 1330535996945,
            "name": "Examplinator 3000",
            "receipts": ["receipt1", "receipt2"],
        }
        app = AppRecord(good_data)
        ok, error = app.validate()
        self.assertTrue(ok)

        good_data_deleted = good_data.copy()
        good_data_deleted["deleted"] = True
        app = AppRecord(good_data_deleted)
        ok, error = app.validate()
        self.assertTrue(ok)

        bad_data = good_data.copy()
        bad_data.pop("origin")
        app = AppRecord(bad_data)
        ok, error = app.validate()
        self.assertFalse(ok)

        bad_data = good_data.copy()
        bad_data["origin"] = 42
        app = AppRecord(bad_data)
        ok, error = app.validate()
        self.assertFalse(ok)

        bad_data = good_data.copy()
        bad_data["name"] = ["name", "must", "be", "a", "string"]
        app = AppRecord(bad_data)
        ok, error = app.validate()
        self.assertFalse(ok)

        bad_data = good_data.copy()
        bad_data["installedAt"] = "the recent past"
        app = AppRecord(bad_data)
        ok, error = app.validate()
        self.assertFalse(ok)

        bad_data = good_data.copy()
        bad_data["receipts"] = "I HACK YOU GIVE ME ALL THE RECEIPTS"
        app = AppRecord(bad_data)
        ok, error = app.validate()
        self.assertFalse(ok)

        bad_data = good_data.copy()
        bad_data["receipts"] = ["I", "HACK", "YOU", 42]
        app = AppRecord(bad_data)
        ok, error = app.validate()
        self.assertFalse(ok)

        bad_data = good_data.copy()
        bad_data["deleted"] = "true"
        app = AppRecord(bad_data)
        ok, error = app.validate()
        self.assertFalse(ok)

    def test_validation_of_device_records(self):
        device = DeviceRecord()
        ok, error = device.validate()
        self.assertFalse(ok)

        good_data = {
            "uuid": "75B538D8-67AF-44E8-86A0-B1A07BE137C8",
            "name": "Anant's Mac Pro",
            "type": "mobile",
            "layout": "android/phone",
            "addedAt": 1330535996745,
            "modifiedAt": 1330535996945,
            "apps": {},
        }
        device = DeviceRecord(good_data)
        ok, error = device.validate()
        self.assertTrue(ok)

        bad_data = good_data.copy()
        bad_data.pop("uuid")
        device = DeviceRecord(bad_data)
        ok, error = device.validate()
        self.assertFalse(ok)

        bad_data = good_data.copy()
        bad_data["uuid"] = good_data["uuid"].lower()
        device = DeviceRecord(bad_data)
        ok, error = device.validate()
        self.assertFalse(ok)

        bad_data = good_data.copy()
        bad_data["uuid"] = good_data["uuid"].replace("-", "")
        device = DeviceRecord(bad_data)
        ok, error = device.validate()
        self.assertFalse(ok)

        bad_data = good_data.copy()
        bad_data["name"] = ["NOT", "A", "STRING"]
        device = DeviceRecord(bad_data)
        ok, error = device.validate()
        self.assertFalse(ok)

        bad_data = good_data.copy()
        bad_data["name"] = ""
        device = DeviceRecord(bad_data)
        ok, error = device.validate()
        self.assertFalse(ok)

        bad_data = good_data.copy()
        bad_data["type"] = ""
        device = DeviceRecord(bad_data)
        ok, error = device.validate()
        self.assertFalse(ok)

        bad_data = good_data.copy()
        bad_data["layout"] = ""
        device = DeviceRecord(bad_data)
        ok, error = device.validate()
        self.assertFalse(ok)

        bad_data = good_data.copy()
        bad_data["modifiedAt"] = "42"
        device = DeviceRecord(bad_data)
        ok, error = device.validate()
        self.assertFalse(ok)

        bad_data = good_data.copy()
        bad_data["apps"] = ["LIST", "INSTEAD", "OF", "DICT"]
        device = DeviceRecord(bad_data)
        ok, error = device.validate()
        self.assertFalse(ok)

    def test_handling_of_unicode_app_origin_string(self):
        good_data = {
            "origin": "https://example.com",
            "manifestPath": "/manifest.webapp",
            "installOrigin": "https://marketplace.mozilla.org",
            "installedAt": 1330535996745,
            "modifiedAt": 1330535996945,
            "name": "Examplinator 3000",
            "receipts": ["receipt1", "receipt2"],
        }

        app1 = AppRecord(good_data)
        ok, error = app1.validate()
        self.assertTrue(ok)

        good_data["origin"] = u"https://\N{SNOWMAN}.com"
        app2 = AppRecord(good_data)
        ok, error = app2.validate()
        self.assertTrue(ok)
        self.assertTrue(isinstance(app2.get_id(), str))

        good_data["origin"] = u"https://example.com"
        app2 = AppRecord(good_data)
        ok, error = app2.validate()
        self.assertTrue(ok)
        self.assertEquals(app1.get_id(), app2.get_id())
