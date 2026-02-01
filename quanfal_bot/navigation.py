"""
Navigation helper for the Quanfal bot.

This module encapsulates logic for moving the player's character
between different crafting stations (e.g. forge, crusher, tailoring
table).  It also provides a simple routine for rotating the camera
until a given on‑screen text appears.  Both behaviours depend on
ui_controller for executing mouse/keyboard actions and on
image_recognition for detecting UI elements.

Because the implementation of these methods is highly game‑specific and
depends on user configuration (e.g. screen resolution, station
coordinates), this module mostly contains placeholders.  Fill in
real logic as you adapt the bot for your environment.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional

from .ui_controller import UIController
from .image_recognition import ImageRecognition
from .gui import BotConfig

logger = logging.getLogger(__name__)


class Navigation:
    """Helper class for navigating between stations in the game world."""

    def __init__(self, ui: UIController, img: ImageRecognition, config: BotConfig) -> None:
        self.ui = ui
        self.img = img
        self.config = config
        # Coordinates of crafting stations; user can extend this as needed
        # These are placeholder values and should be replaced with actual
        # screen coordinates (x, y) where the corresponding station can
        # be clicked to interact with it.
        self.stations: Dict[str, tuple[int, int]] = {
            "forge": (100, 200),      # кузнечное горнило
            "crusher": (300, 400),    # дробилка
            "jewelry": (500, 600),    # ювелирный станок
            "tailor": (700, 800),     # портняжное дело
        }

    def move_to_station(self, name: str) -> None:
        """Move player to the given station by clicking on preconfigured coordinates."""
        coords = self.stations.get(name)
        if not coords:
            logger.warning("Unknown station '%s'; cannot navigate", name)
            return
        x, y = coords
        logger.info("Moving to station '%s' at %s", name, coords)
        try:
            # Move mouse to station and click; adjust duration as needed
            self.ui.move_to(x, y, duration=0.2)
            time.sleep(0.1)
            self.ui.click(x, y, button="left")
        except NotImplementedError:
            logger.warning("UI automation not implemented; cannot move to station")

    def rotate_camera_until(self, keyword: str, timeout: float = 10.0) -> bool:
        """Rotate camera until text appears on screen.

        Parameters
        ----------
        keyword: str
            The text to search for on the screen (e.g. "дробилка").
        timeout: float
            Maximum time in seconds to spend rotating before giving up.

        Returns
        -------
        bool
            True if the keyword was detected, False otherwise.
        """
        start = time.time()
        logger.info("Rotating camera to find '%s'", keyword)
        while time.time() - start < timeout:
            try:
                # Simulate holding left mouse button and moving horizontally to rotate
                # Adjust the distance and duration as needed for your game
                self.ui.move_to(400, 300)  # Move to screen centre
                self.ui.drag = getattr(self.ui, "drag", None)
                # If drag is available via pyautogui, we use it; otherwise do nothing
                if self.ui.drag:
                    self.ui.drag([(400, 300), (200, 300)], keys=["left"])
                else:
                    # Fallback: move mouse left and right to rotate
                    self.ui.move_to(200, 300)
            except NotImplementedError:
                logger.warning("UI automation not implemented; cannot rotate camera")
                return False
            # Take a screenshot and search for the keyword using template matching or OCR
            try:
                screenshot = self.ui.screenshot()
            except NotImplementedError:
                logger.warning("Cannot take screenshot; rotation aborted")
                return False
            # Attempt to detect the keyword by matching templates
            # For simplicity, we just log and return False here.
            # You could extend this to run OCR or template matching on 'screenshot'.
            logger.debug("Searching for keyword '%s' in screenshot (not implemented)", keyword)
            time.sleep(0.5)
            # For now, assume we never find the keyword in this dummy implementation
        logger.info("Failed to find '%s' within %.1f seconds", keyword, timeout)
        return False