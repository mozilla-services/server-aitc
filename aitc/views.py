# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import simplejson as json

from pyramid.security import Authenticated, Allow

#from mozsvc.metrics import MetricsService
from cornice.service import Service


class AITCService(Service):
    """Custom Service class to assist DRY in the AITC project.

    This Service subclass provides useful defaults for AITC service
    endpoints, such as configuring authentication and path prefixes.
    """

    def __init__(self, **kwds):
        # Configure DRY defaults for the path.
        kwds["path"] = self._configure_the_path(kwds["path"])
        # Ensure all views require an authenticated user.
        #kwds.setdefault("permission", "owner")
        kwds.setdefault("acl", self._default_acl)
        super(AITCService, self).__init__(**kwds)

    def _configure_the_path(self, path):
        """Helper method to apply default configuration of the service path."""
        # Insert pattern-matching regexes into the path
        path = path.replace("{collection}", "{collection:[a-z]+}")
        path = path.replace("{item}", "{item:[a-zA-Z0-9._-]+}")
        # Add path prefix for the API version number and userid.
        path = "/{api:1.0}/{userid:[0-9]{1,10}}" + path
        return path

    def _default_acl(self, request):
        """Default ACL: only the owner is allowed access."""
        return [(Allow, request.matchdict["userid"], "owner")]


root = AITCService(name="root", path="/")
collection = AITCService(name="collection", path="/{collection}/")
item = AITCService(name="item", path="/{collection}/{item}")


def _ctrl(request):
    return request.registry["aitc.controller"]


@collection.get(renderer="simplejson")
def get_collection(request):
    return _ctrl(request).get_collection(request)


@item.get(renderer="simplejson")
def get_item(request):
    return _ctrl(request).get_item(request)


@item.put()
def put_item(request):
    return _ctrl(request).set_item(request)


@item.delete()
def delete_item(request):
    return _ctrl(request).delete_item(request)
