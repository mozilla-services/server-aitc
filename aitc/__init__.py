# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
try:
    from gevent import monkey
    from gevent_zeromq import monkey_patch
    monkey.patch_all()
    monkey_patch()
except ImportError:
    pass

from mozsvc.config import get_configurator
from mozsvc.plugin import load_from_settings

from aitc.controller import AITCController


def includeme(config):
    # Add exception logging.
    # Putting it first prevents other things from converting errors
    # into HTTP responses before we get to see them.
    config.include("aitc.tweens")
    # Include the basic mozsvc project dependencies.
    config.include("cornice")
    config.include("mozsvc")
    config.include("mozsvc.user.whoauth")
    # Re-use some framework stuff from syncstorage.
    config.include("syncstorage.tweens")
    config.include("syncstorage.storage")
    # Add in the stuff we define ourselves.
    config.scan("aitc.views")
    # Create the "controller" object for handling requests.
    config.registry["aitc.controller"] = AITCController(config)


def main(global_config, **settings):
    config = get_configurator(global_config, **settings)
    metlog_wrapper = load_from_settings('metlog', config.registry.settings)
    config.registry['metlog'] = metlog_wrapper.client
    config.begin()
    try:
        config.include(includeme)
    finally:
        config.end()
    return config.make_wsgi_app()
