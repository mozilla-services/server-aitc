# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import hashlib
import simplejson as json

from pyramid.httpexceptions import (HTTPNotFound,
                                    HTTPForbidden,
                                    HTTPRequestEntityTooLarge,
                                    HTTPUnsupportedMediaType)

from mozsvc.exceptions import ERROR_MALFORMED_JSON, ERROR_INVALID_OBJECT
from mozsvc.metrics import update_mozsvc_data

from syncstorage.controller import StorageController, HTTPJsonBadRequest

from aitc import records


MAX_ITEM_SIZE = 8 * 1024


class AITCController(object):
    """Storage request controller for AITC.

    This is a skinny wrapper around a SyncStorage controller that speaks
    the diff between the two protocols.
    """

    # This maps collection names to Record class objects that
    # can be used for parsing/validating the items in that collection.
    # Any collection name not in this dict will will not be accessible.
    RECORD_CLASSES = {
        "apps": records.AppRecord,
        "devices": records.DeviceRecord,
    }

    def __init__(self, config):
        self.controller = StorageController(config)
        key = "storage.ignore_unknown_fields"
        self.ignore_unknown_fields = config.registry.settings.get(key, False)

    def get_collection(self, request):
        """Get the list of items from a collection."""
        kwds = {"full": "1"}
        collection = request.matchdict["collection"]
        if "after" in request.GET:
            kwds["newer"] = request.GET["after"]
        try:
            bsos = self.controller.get_collection(request, **kwds)["items"]
        except HTTPNotFound:
            bsos = []
        items = (json.loads(bso["payload"]) for bso in bsos)
        if "full" not in request.GET:
            items = (self._abbreviate_item(request, item) for item in items)
        items = list(items)
        for item in items:
            self._log_record_seen(request, collection, item)
        return {collection: items}

    def get_item(self, request):
        """Get a single item by ID."""
        bso = self.controller.get_item(request)
        item = json.loads(bso["payload"])
        self._log_record_seen(request, request.matchdict["collection"], item)
        return item

    def set_item(self, request):
        """Upload a new item by ID."""
        # Validate the incoming data.
        if request.content_type not in ("application/json", None):
            msg = "Unsupported Media Type: %s" % (request.content_type,)
            raise HTTPUnsupportedMediaType(msg)
        if len(request.body) > MAX_ITEM_SIZE:
            raise HTTPRequestEntityTooLarge()
        try:
            data = json.loads(request.body)
        except ValueError:
            raise HTTPJsonBadRequest(ERROR_MALFORMED_JSON)
        item = self._parse_item(request, data)
        # Check that we're putting it with the right id.
        # Unfortunately we have to *return* the error response here
        # rather than raise it, because raising HTTPForbidden will
        # trigger pyramid's prompt-for-credentials handlers.
        if request.matchdict["item"] != item.get_id():
            return HTTPForbidden("Item ID does not match origin")
        self._log_record_seen(request, request.matchdict["collection"], item)
        # Pass through to storage.
        # Requires another round-trip through JSON; yuck.
        request.body = json.dumps({"payload": json.dumps(item)})
        return self.controller.set_item(request)

    def delete_item(self, request):
        """Delete a single item by ID."""
        return self.controller.delete_item(request)

    def _parse_item(self, request, data):
        """Parse and validate data for a single item."""
        # Find the correct type of Record object to create.
        try:
            RecordClass = self.RECORD_CLASSES[request.matchdict["collection"]]
        except KeyError:
            raise HTTPNotFound()
        # Load the data into an object of that type.
        try:
            kwds = {"ignore_unknown_fields": self.ignore_unknown_fields}
            item = RecordClass(data, **kwds)
        except ValueError:
            raise HTTPJsonBadRequest(ERROR_INVALID_OBJECT)
        # Get any existing values for that item.
        try:
            old_bso = self.controller.get_item(request)
            old_item = json.loads(old_bso["payload"])
        except HTTPNotFound:
            old_item = None
        # Fill in missing values and validate.
        item.populate(request, old_item)
        ok, error = item.validate()
        if not ok:
            raise HTTPJsonBadRequest(ERROR_INVALID_OBJECT)
        return item

    def _abbreviate_item(self, request, data):
        """Produce abbreviated data for a single item."""
        try:
            RecordClass = self.RECORD_CLASSES[request.matchdict["collection"]]
        except KeyError:  # pragma nocover
            raise HTTPNotFound()
        # Don't error out if the database contains items with unknown fields.
        item = RecordClass(data, ignore_unknown_fields=True)
        return item.abbreviate()

    def _log_record_seen(self, request, collection, item):
        """Log the fact that a record has been seen by a particular client.

        This method is a hook for metrics logging.  It gets called each time
        that a record is sent to or received from a client, and logs that
        information for future reporting and analysis.
        """
        if collection == "apps":
            fingerpint = hashlib.sha1()
            fingerprint.update(request.user["uid"])
            fingerprint.update(request.headers.get("User-Agent", ""))
            fingerprint.update(item["origin"])
            if item.get("hidden", False):
                action = "uninstall"
            else:
                action = "install"
            update_mozsvc_data({
                "aitc.fingerprint": fingerprint.hexdigest(),
                "aitc.action": action,
            })
