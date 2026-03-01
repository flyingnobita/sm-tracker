"""CLI package for sm-tracker."""

import sm_tracker.cli.auth  # noqa: F401
import sm_tracker.cli.config  # noqa: F401
import sm_tracker.cli.history  # noqa: F401
import sm_tracker.cli.show  # noqa: F401
import sm_tracker.cli.track  # noqa: F401
from sm_tracker.cli.app import app

__all__ = ["app"]
