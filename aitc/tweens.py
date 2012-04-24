# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import traceback


def log_all_errors(handler, registry):
    """Tween to log all errors via metlog."""

    def log_all_errors_tween(request):
        try:
            return handler(request)
        except Exception:
            logger = request.registry["metlog"]
            err = traceback.format_exc()
            logger.exception(err)
            raise

    return log_all_errors_tween


def includeme(config):
    config.add_tween("aitc.tweens.log_all_errors")
