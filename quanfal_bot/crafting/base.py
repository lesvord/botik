"""
Base classes for crafting modules in the Quanfal bot.

Every crafting profession (blacksmithing, jewelling, tailoring) should
inherit from ``CraftingModule`` and implement the following methods:

* ``run_cycle`` – perform one complete crafting cycle: gather materials,
  craft items, collect them and post‑process (e.g. dismantle into
  crusher if necessary).  The base implementation provides a stub
  raising NotImplementedError.

``CraftingModule`` receives instances of ``UIController``,
``Navigation`` and ``ImageRecognition`` via its constructor along
with the global ``BotConfig``.  Subclasses should use these to
perform their tasks.
"""

from __future__ import annotations

import logging
from typing import Any

from ..ui_controller import UIController
from ..navigation import Navigation
from ..image_recognition import ImageRecognition
from ..gui import BotConfig

logger = logging.getLogger(__name__)


class CraftingModule:
    """Abstract base class for a crafting profession.

    Subclasses must implement ``run_cycle``.
    """

    name: str = "unnamed"

    def __init__(self,
                 ui: UIController,
                 nav: Navigation,
                 img: ImageRecognition,
                 config: BotConfig) -> None:
        self.ui = ui
        self.nav = nav
        self.img = img
        self.config = config

    def run_cycle(self) -> None:
        """Perform a full cycle of actions for this profession.

        A typical cycle includes:

        1. Navigating to the appropriate crafting station.
        2. Opening the crafting interface and selecting the recipe.
        3. Initiating the craft and waiting for completion.
        4. Collecting crafted items and moving them to the inventory.
        5. Post‑processing: dismantling items of unwanted grades.
        
        Subclasses should override this method to implement their
        profession‑specific logic.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"