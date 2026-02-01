"""
Image processing utilities for the Quanfal bot.

This module provides helper functions to perform template matching
using OpenCV (cv2) to locate UI elements on the screen, as well as
simple heuristics to determine item grade based on border colour.  It
does not implement optical character recognition; instead it relies on
PNG templates supplied by the user via configuration.

OpenCV is required for template matching.  If cv2 cannot be imported,
the methods in this class will raise NotImplementedError.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

from PIL import Image

logger = logging.getLogger(__name__)

try:
    import cv2  # type: ignore
    _has_cv2 = True
except ImportError:
    cv2 = None  # type: ignore
    _has_cv2 = False


class ImageRecognition:
    """Helper class for performing template matching and grade detection."""

    def __init__(self, config) -> None:
        self.config = config
        # Support for both single‑item and multi‑item configurations.  If
        # ``config`` has an ``items`` attribute, we assume it is a list of
        # ``ItemConfig`` objects.  Otherwise, we fall back to a single set
        # of grade icons on the config itself.
        self._grade_templates: Dict[str, Optional[np.ndarray]] = {}
        self.item_templates: List[Dict[str, Optional[np.ndarray]]] = []
        # Multi‑item: load templates for each item
        if hasattr(config, 'items'):
            for item in config.items:
                templates: Dict[str, Optional[np.ndarray]] = {}
                for grade, path in item.grade_icons.items():
                    if path:
                        try:
                            templates[grade] = self._load_template(path)
                        except Exception as e:
                            logger.warning("Failed to load grade template '%s': %s", path, e)
                            templates[grade] = None
                    else:
                        templates[grade] = None
                self.item_templates.append(templates)
            # For backward compatibility, build a merged template dict of the first item
            if self.item_templates:
                self._grade_templates = self.item_templates[0].copy()
        else:
            # Single‑item fallback
            for grade, path in getattr(config, 'grade_icons', {}).items():
                if path:
                    try:
                        self._grade_templates[grade] = self._load_template(path)
                    except Exception as e:
                        logger.warning("Failed to load grade template '%s': %s", path, e)
                        self._grade_templates[grade] = None
                else:
                    self._grade_templates[grade] = None

    @staticmethod
    def _load_template(path: str) -> np.ndarray:
        """Load an image file into a grayscale numpy array."""
        if not _has_cv2:
            raise NotImplementedError("cv2 is required for template loading")
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(path)
        return img

    def match_template(self, screenshot: Image.Image, template: np.ndarray, threshold: float = 0.8) -> Optional[Tuple[int, int]]:
        """
        Search for the given template within the screenshot.

        Parameters
        ----------
        screenshot: PIL.Image
            Full‑colour screenshot of the game.
        template: np.ndarray
            Grayscale template image loaded via ``_load_template``.
        threshold: float
            Match threshold between 0 and 1.

        Returns
        -------
        Optional[Tuple[int, int]]
            Coordinates (x, y) of the top‑left corner of the best match
            if the matching score exceeds ``threshold``; otherwise
            ``None``.
        """
        if not _has_cv2:
            raise NotImplementedError("cv2 is required for template matching")
        # Convert screenshot to grayscale
        img_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGR2GRAY)
        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        logger.debug("Template match score: %s", max_val)
        if max_val >= threshold:
            return max_loc
        return None

    def locate_button(self, screenshot: Image.Image, button_name: str, templates: Dict[str, str], threshold: float = 0.8) -> Optional[Tuple[int, int]]:
        """
        Generic helper to locate a named button using a set of possible templates.

        For example, to locate the "Создать" button, you could supply
        ``templates={"create": "/path/to/create_button.png"}`` and
        call ``locate_button(screenshot, "create", templates)``.
        """
        if not _has_cv2:
            raise NotImplementedError("cv2 is required for locate_button")
        for name, path in templates.items():
            try:
                tpl = self._load_template(path)
            except Exception as e:
                logger.warning("Could not load template for button %s: %s", name, e)
                continue
            pos = self.match_template(screenshot, tpl, threshold)
            if pos is not None:
                logger.info("Found button %s at %s", button_name, pos)
                return pos
        return None

    def detect_item_grade(self, item_image: Image.Image) -> Optional[str]:
        """
        Very simple heuristic for determining item grade based on the colour
        of its border.  This assumes that the game draws a coloured border
        around item icons to indicate their rarity/quality.

        The method samples pixels at the border of the icon and compares
        their average colour to known grade colours.  The mapping of
        grade names to RGB tuples must be defined in ``GRADE_COLOURS``
        below.  You may need to adjust this mapping for your game's
        colour palette.
        """
        # Known grade colours (R, G, B)
        GRADE_COLOURS: Dict[str, Tuple[int, int, int]] = {
            "серый": (128, 128, 128),
            "зелёный": (0, 255, 0),
            "синий": (0, 128, 255),
            "фиолетовый": (128, 0, 128),
            "жёлтый": (255, 255, 0),
        }
        img_np = np.array(item_image)
        # Extract border pixels (top, bottom, left, right)
        border_pixels = np.concatenate([
            img_np[0, :, :],
            img_np[-1, :, :],
            img_np[:, 0, :],
            img_np[:, -1, :],
        ])
        avg_color = border_pixels.mean(axis=0)
        logger.debug("Average border color: %s", avg_color)
        # Determine closest grade by Euclidean distance
        best_grade = None
        best_dist = float("inf")
        for grade, colour in GRADE_COLOURS.items():
            dist = np.linalg.norm(avg_color - np.array(colour))
            if dist < best_dist:
                best_dist = dist
                best_grade = grade
        return best_grade

    def find_items_by_template(self, screenshot: Image.Image, template: np.ndarray, region: Tuple[int, int, int, int], threshold: float = 0.8) -> List[Tuple[int, int]]:
        """
        Find all occurrences of a template inside a subregion of the screenshot.

        Returns a list of coordinates where the template matches.  The
        region is given as (left, top, width, height) in absolute screen
        coordinates.
        """
        if not _has_cv2:
            raise NotImplementedError("cv2 is required for template matching")
        left, top, width, height = region
        # Crop region
        sub_img = screenshot.crop((left, top, left + width, top + height))
        img_gray = cv2.cvtColor(np.array(sub_img), cv2.COLOR_BGR2GRAY)
        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        yloc, xloc = np.where(res >= threshold)
        positions = []
        for (x, y) in zip(xloc, yloc):
            positions.append((left + x, top + y))
        return positions