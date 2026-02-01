"""
Tailoring module for the Quanfal bot.

This is a placeholder implementation.  Tailoring often involves
similar steps to blacksmithing (navigate to the tailoring station,
select recipe, craft items, collect outputs and dismantle unwanted
grades).  To activate this module, implement ``run_cycle`` with the
appropriate UI coordinates.
"""

from __future__ import annotations

import logging

from .base import CraftingModule

logger = logging.getLogger(__name__)


class Tailoring(CraftingModule):
    name = "tailoring"

    def run_cycle(self) -> None:
        logger.info("Tailoring module is not implemented yet.")