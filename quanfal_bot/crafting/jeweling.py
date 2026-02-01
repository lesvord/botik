"""
Jewelling module for the Quanfal bot.

Currently this module is a simple stub.  To enable automatic
crafting for jewelling, implement ``run_cycle`` similarly to
``Blacksmithing`` but adjust the UI interactions for the jeweller's
bench.  You can enable or disable this module via the GUI.
"""

from __future__ import annotations

import logging

from .base import CraftingModule

logger = logging.getLogger(__name__)


class Jeweling(CraftingModule):
    name = "jeweling"

    def run_cycle(self) -> None:
        logger.info("Jewelling module is not implemented yet.")