# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import simplejson as json

from pyramid.httpexceptions import (HTTPNotFound,
                                    HTTPForbidden,
                                    HTTPRequestEntityTooLarge)

from mozsvc.exceptions import ERROR_MALFORMED_JSON, ERROR_INVALID_OBJECT

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

    def get_collection(self, request):
        """Get the list of items from a collection."""
        kwds = {"full": "1"}
        if "after" in request.GET:
            kwds["newer"] = request.GET["after"]
        try:
            bsos = self.controller.get_collection(request, **kwds)["items"]
        except HTTPNotFound:
            bsos = []
        items = (json.loads(bso["payload"]) for bso in bsos)
        if "full" not in request.GET:
            items = (self._abbreviate_item(request, item) for item in items)
        return {request.matchdict["collection"]: list(items)}

    def get_item(self, request):
        """Get a single item by ID."""
        bso = self.controller.get_item(request)
        return json.loads(bso["payload"])

    def set_item(self, request):
        """Upload a new item by ID."""
        # Validate the incoming data.
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
            item = RecordClass(data)
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
        item = RecordClass(data)
        return item.abbreviate()
