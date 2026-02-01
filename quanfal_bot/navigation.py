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

# Optional OCR support
try:
    import pytesseract  # type: ignore
    _has_pytesseract = True
except ImportError:
    pytesseract = None  # type: ignore
    _has_pytesseract = False
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
        """Move player to the given station.

        This implementation avoids clicking predefined coordinates because the user
        prefers to rotate the camera and interact via the 'E' key after the
        station label (e.g., "кузнечное горнило", "дробилка") appears on screen.
        The method logs the intent but does not move the cursor.
        """
        coords = self.stations.get(name)
        if not coords:
            logger.warning("Unknown station '%s'; cannot navigate", name)
            return
        logger.info("Preparing to navigate to station '%s' (camera-based)", name)
        # We intentionally do not click on preconfigured coordinates here.
        # Camera navigation will be handled via rotate_camera_until() and pressing 'E'.

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
                # Rotate camera by dragging the mouse to the left.  We move to
                # the centre first, then drag relative using our UIController's
                # drag_rel method.  Adjust dx/dy as needed for your game.
                self.ui.move_to(400, 300)  # Move to screen centre
                try:
                    self.ui.drag_rel(-200, 0, duration=0.3, button="left")
                except AttributeError:
                    # If drag_rel is not available, fallback to simple move
                    self.ui.move_to(200, 300)
            except NotImplementedError:
                logger.warning("UI automation not implemented; cannot rotate camera")
                return False
            # Take a screenshot and search for the keyword using OCR
            try:
                screenshot = self.ui.screenshot()
            except NotImplementedError:
                logger.warning("Cannot take screenshot; rotation aborted")
                return False
            # Perform OCR if available
            found = False
            if _has_pytesseract:
                try:
                    # Convert screenshot to text; force Russian language if available
                    text = pytesseract.image_to_string(screenshot, lang="rus", config="--psm 6").lower()
                    if keyword.lower() in text:
                        logger.info("Detected keyword '%s' via OCR", keyword)
                        return True
                except Exception as e:
                    logger.warning("OCR failed: %s", e)
            # Could be extended with template matching here
            # Wait briefly before continuing rotation
            time.sleep(0.5)
        # Keyword not found within timeout
        logger.info("Failed to find '%s' within %.1f seconds", keyword, timeout)
        return False