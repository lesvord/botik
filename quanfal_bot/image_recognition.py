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

        # Load trigger templates for each item.  Each item may specify
        # additional image templates (e.g. item name, create button,
        # empty slot, inventory slot).  These templates are stored in
        # ``self.item_triggers`` as a list of dictionaries keyed by
        # trigger name.
        self.item_triggers: List[Dict[str, Optional[np.ndarray]]] = []
        if hasattr(config, 'items'):
            for item in config.items:
                triggers_dict: Dict[str, Optional[np.ndarray]] = {}
                # Ensure 'triggers' is present on item
                trigger_conf = getattr(item, 'triggers', {}) or {}
                for key, path in trigger_conf.items():
                    if path:
                        try:
                            triggers_dict[key] = self._load_template(path)
                        except Exception as e:
                            logger.warning("Failed to load trigger template '%s' for key '%s': %s", path, key, e)
                            triggers_dict[key] = None
                    else:
                        triggers_dict[key] = None
                self.item_triggers.append(triggers_dict)

        # Attempt to import pytesseract for OCR functionality.  OCR is used to
        # locate UI elements by their textual labels (e.g., button captions or
        # recipe names) when template matching is unavailable or insufficient.
        try:
            import pytesseract  # type: ignore
            self._pytesseract = pytesseract
            self._has_ocr = True
        except Exception:
            # If pytesseract is not available, OCR methods will not work
            self._pytesseract = None
            self._has_ocr = False

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

    # ------------------------------------------------------------------
    # OCR METHODS
    #
    # The methods below rely on pytesseract to perform optical character
    # recognition on screenshots.  This allows the bot to locate UI elements
    # such as buttons or item names based solely on their text, without
    # requiring pre‑captured templates.  If pytesseract is not installed,
    # these methods will raise NotImplementedError.

    def locate_text(self, screenshot: Image.Image, target_text: str, lang: str = "rus+eng") -> Optional[Tuple[int, int, int, int]]:
        """
        Find the first occurrence of ``target_text`` within the screenshot using OCR.

        Parameters
        ----------
        screenshot : PIL.Image
            The full‑colour screenshot to search.
        target_text : str
            The exact or partial text to look for (case‑insensitive).
        lang : str
            Languages to use for OCR (default "rus+eng").  You should
            configure Tesseract with these language packs installed.

        Returns
        -------
        Optional[Tuple[int, int, int, int]]
            Returns the bounding box (x, y, w, h) of the first match, or
            ``None`` if no match is found or OCR is unavailable.
        """
        if not self._has_ocr:
            raise NotImplementedError("pytesseract is required for locate_text")
        # Convert screenshot to RGB (pytesseract requires this format)
        img_rgb = screenshot.convert("RGB")
        # Perform OCR; request data with bounding boxes
        try:
            ocr_data = self._pytesseract.image_to_data(img_rgb, lang=lang, output_type=self._pytesseract.Output.DICT)
        except Exception as e:
            logger.warning("OCR failed: %s", e)
            return None
        target_lower = target_text.lower().strip()
        # Iterate over detected words and find the first one containing the target
        n_boxes = len(ocr_data.get("text", []))
        for i in range(n_boxes):
            text = ocr_data["text"][i]
            if not text:
                continue
            if target_lower in text.lower():
                x = ocr_data["left"][i]
                y = ocr_data["top"][i]
                w = ocr_data["width"][i]
                h = ocr_data["height"][i]
                logger.debug("Located text '%s' at (%s,%s,%s,%s)", text, x, y, w, h)
                return (x, y, w, h)
        return None