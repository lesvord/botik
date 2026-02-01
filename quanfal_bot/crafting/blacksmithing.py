"""
Blacksmithing module for the Quanfal bot.

Implements the logic for automatically crafting a single item (as
specified by ``config.craft_item_name``) at the forge and handling
the resulting items.  When the inventory becomes full, the module
automatically moves to the crusher to dismantle items of selected
grades.

Due to the highly interactive nature of games, many of the methods
below are placeholders that need to be completed for your specific
setup.  Pay particular attention to the coordinates and UI elements
in your game client.
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Tuple, List

from .base import CraftingModule

logger = logging.getLogger(__name__)


class Blacksmithing(CraftingModule):
    name = "blacksmithing"

    def run_cycle(self) -> None:
        """Perform a crafting cycle for each configured item.

        The blacksmithing module now iterates through all items configured
        in ``self.config.items``, crafting each one in sequence.  For
        each item the recipe is selected based on its name and grade
        preferences and icons specific to that item are used during
        dismantling.
        """
        # Iterate over each item configuration
        for item_cfg in getattr(self.config, "items", [self.config]):
            try:
                name = item_cfg.craft_item_name
            except AttributeError:
                # Backwards compatibility: config may be single item
                name = getattr(self.config, "craft_item_name", "")
            logger.info("Starting blacksmithing cycle for %s", name)
            # 1. Move to forge (camera-based; does not click)
            self.nav.move_to_station("forge")
            # 2. Rotate camera until the forge name appears. If not found, skip crafting this item.
            found_forge = False
            try:
                found_forge = self.nav.rotate_camera_until("кузнечное горнило", timeout=8.0)
            except Exception as e:
                logger.warning("Rotation to find forge raised an exception: %s", e)
            if not found_forge:
                logger.warning("Could not detect forge on screen; skipping %s", name)
                continue
            # 3. Interact with forge by pressing 'e'
            self.open_crafting_interface()
            # 4. Select recipe
            self.select_recipe(name)
            # 5. Initiate crafting
            self.start_craft(item_cfg)
            # 5. Collect items from output slots until bag is full
            while True:
                if not self.collect_items_from_output(item_cfg):
                    # If items remain in output after collection, we assume bag is full
                    self.handle_full_inventory(item_cfg)
                    break
                # Continue crafting next batch if output was cleared successfully
                time.sleep(0.5)
                # Optionally click "Создать" again
                self.start_craft(item_cfg)

    # ----- Helper methods -----
    def open_crafting_interface(self) -> None:
        """Open the blacksmithing interface.

        In many games this requires clicking on the station or pressing
        a key.  Adjust this implementation as needed.  Here we simply
        press the interaction key 'e'.
        """
        try:
            self.ui.press('e')
            logger.debug("Pressed 'e' to open crafting interface")
        except NotImplementedError:
            logger.warning("Cannot send keypress; crafting interface may not open")

    def select_recipe(self, item_name: str, item_cfg=None) -> None:
        """Select the recipe corresponding to ``item_name`` in the crafting menu.

        Typically the recipe list is on the left side of the crafting
        window.  We type into the search box and select the first result.
        """
        logger.info("Selecting recipe '%s'", item_name)
        # Attempt to use template matching if a trigger image is provided for the item.
        template = None
        item_index = None
        if item_cfg is not None and hasattr(self.config, 'items'):
            try:
                item_index = self.config.items.index(item_cfg)
            except ValueError:
                item_index = None
        if item_index is not None and item_index < len(self.img.item_triggers):
            template = self.img.item_triggers[item_index].get('item')
        if template is not None:
            # Search entire screen for the template
            try:
                screenshot = self.ui.screenshot()
            except NotImplementedError:
                screenshot = None
            if screenshot is not None:
                pos = None
                try:
                    pos = self.img.match_template(screenshot, template, threshold=0.8)
                except Exception:
                    pos = None
                if pos:
                    x, y = pos
                    try:
                        self.ui.click(x + template.shape[1] // 2, y + template.shape[0] // 2, button="left")
                        logger.debug("Clicked on recipe '%s' using template at (%s,%s)", item_name, x, y)
                        time.sleep(0.3)
                        return
                    except NotImplementedError:
                        logger.warning("UI automation not available; cannot click recipe via template")
        # Fallback: OCR scanning through list region with scrolling
        # Define region of the recipe list on the left side of the crafting interface.
        recipe_region: Tuple[int, int, int, int] = (50, 250, 300, 450)
        found = False
        for attempt in range(6):
            try:
                screenshot = self.ui.screenshot()
            except NotImplementedError:
                screenshot = None
            bbox: Optional[Tuple[int, int, int, int]] = None
            if screenshot is not None:
                left, top, width, height = recipe_region
                sub_img = screenshot.crop((left, top, left + width, top + height))
                try:
                    bbox = self.img.locate_text(sub_img, item_name)
                except Exception:
                    bbox = None
            if bbox:
                x, y, w, h = bbox
                click_x = recipe_region[0] + x + w // 2
                click_y = recipe_region[1] + y + h // 2
                try:
                    self.ui.click(click_x, click_y, button="left")
                    logger.debug("Clicked on recipe '%s' at (%s,%s) using OCR", item_name, click_x, click_y)
                    time.sleep(0.3)
                    found = True
                    break
                except NotImplementedError:
                    logger.warning("UI automation not available; cannot click recipe via OCR")
                    break
            try:
                self.ui.scroll(-300, x=recipe_region[0] + recipe_region[2] // 2,
                               y=recipe_region[1] + recipe_region[3] // 2)
                time.sleep(0.4)
            except NotImplementedError:
                logger.warning("UI automation not available; cannot scroll recipe list")
                break
        if not found:
            logger.warning("Could not locate recipe '%s' via template or OCR", item_name)

    def start_craft(self, item_cfg=None) -> None:
        """Locate and click the 'Создать' button to start crafting.

        Optionally accepts ``item_cfg`` which provides grade icon paths.  If
        provided, the method looks for a template named "создать" in
        ``item_cfg.grade_icons``; otherwise it falls back to a generic
        approach.
        """
        logger.info("Attempting to start crafting")
        # First, attempt to click the create button using a provided trigger image
        template = None
        item_index = None
        if item_cfg is not None and hasattr(self.config, 'items'):
            try:
                item_index = self.config.items.index(item_cfg)
            except ValueError:
                item_index = None
        if item_index is not None and item_index < len(self.img.item_triggers):
            template = self.img.item_triggers[item_index].get('create')
        if template is not None:
            try:
                screenshot = self.ui.screenshot()
            except NotImplementedError:
                screenshot = None
            if screenshot is not None:
                pos = None
                try:
                    pos = self.img.match_template(screenshot, template, threshold=0.8)
                except Exception:
                    pos = None
                if pos:
                    x, y = pos
                    try:
                        self.ui.click(x + template.shape[1] // 2, y + template.shape[0] // 2, button="left")
                        logger.debug("Clicked 'Создать' via create trigger at (%s,%s)", x, y)
                        return
                    except NotImplementedError:
                        logger.warning("UI automation not available; cannot click 'Создать' via template")
        # Next, try OCR to locate the 'Создать' text on screen
        screenshot = None
        try:
            screenshot = self.ui.screenshot()
        except NotImplementedError:
            pass
        if screenshot is not None:
            try:
                bbox = self.img.locate_text(screenshot, "создать")
            except Exception:
                bbox = None
            if bbox:
                x, y, w, h = bbox
                cx, cy = x + w // 2, y + h // 2
                try:
                    self.ui.click(cx, cy, button="left")
                    logger.debug("Clicked 'Создать' via OCR at (%s,%s)", cx, cy)
                    return
                except NotImplementedError:
                    logger.warning("Cannot click 'Создать' via OCR")
        # Fallback to global grade icon template if provided
        screenshot = None
        try:
            screenshot = self.ui.screenshot()
        except NotImplementedError:
            pass
        if screenshot is not None:
            templates = {}
            if item_cfg is not None:
                try:
                    for grade, path in item_cfg.grade_icons.items():
                        if grade.lower() == "создать" and path:
                            templates["create"] = path
                            break
                except Exception:
                    pass
            if not templates and hasattr(self.config, "grade_icons"):
                for grade, path in getattr(self.config, "grade_icons", {}).items():
                    if grade.lower() == "создать" and path:
                        templates["create"] = path
                        break
            if templates:
                try:
                    pos = self.img.locate_button(screenshot, "create", templates, threshold=0.8)
                except Exception:
                    pos = None
                if pos:
                    x, y = pos
                    try:
                        self.ui.click(x + 10, y + 10, button="left")
                        logger.debug("Clicked 'Создать' via fallback template at %s", pos)
                        return
                    except NotImplementedError:
                        logger.warning("Cannot click 'Создать' via fallback template")
        # Last fallback: press keyboard shortcut (assumed 'c')
        try:
            self.ui.press('c')
            logger.debug("Pressed 'c' as fallback to start crafting")
        except NotImplementedError:
            logger.warning("No method available to start crafting")

    def collect_items_from_output(self, item_cfg=None) -> bool:
        """Collect items from crafting output slots.

        Returns True if output was successfully emptied, False if items
        remained after collection (indicating that the inventory is full).
        This method attempts to use an empty slot trigger image, if provided
        in the item's configuration, to determine when a slot is empty.
        """
        logger.info("Collecting items from output slots")
        # Coordinates of output slots or region should be configured.  If the user
        # provided a craft_window_region in the configuration, we can derive
        # positions relative to that region.  Otherwise, use placeholder
        # coordinates.
        output_slots: List[Tuple[int, int]]
        if getattr(self.config, "craft_window_region", None):
            left, top, width, height = self.config.craft_window_region  # type: ignore
            # Assume a 3x2 grid of slots within this region
            cols = 3
            rows = 2
            slot_w = width // cols
            slot_h = height // rows
            positions: List[Tuple[int, int]] = []
            for row in range(rows):
                for col in range(cols):
                    cx = left + col * slot_w + slot_w // 2
                    cy = top + row * slot_h + slot_h // 2
                    positions.append((cx, cy))
            output_slots = positions
        else:
            output_slots = [
                (800, 350), (850, 350), (900, 350),
                (800, 400), (850, 400), (900, 400),
            ]
        # Determine empty slot template for this item
        empty_template = None
        if item_cfg is not None and hasattr(self.config, 'items'):
            try:
                idx = self.config.items.index(item_cfg)
            except ValueError:
                idx = None
            if idx is not None and idx < len(self.img.item_triggers):
                empty_template = self.img.item_triggers[idx].get('empty_slot')
        bag_full = False
        for (x, y) in output_slots:
            try:
                self.ui.click(x, y, button="right")
                time.sleep(0.3)
                # After moving, capture a small region around the slot
                try:
                    slot_img = self.ui.screenshot(region=(x - 15, y - 15, 30, 30))
                except NotImplementedError:
                    # Cannot take screenshot; assume collection succeeded
                    continue
                # If empty template provided, use template matching to determine
                # whether the slot became empty.  Otherwise, fall back to
                # brightness heuristic.
                if empty_template is not None:
                    try:
                        pos = self.img.match_template(slot_img, empty_template, threshold=0.7)
                    except Exception:
                        pos = None
                    # If template matching fails (no match), assume item remains (bag full)
                    if pos is None:
                        bag_full = True
                        logger.debug("Slot at (%s,%s) did not match empty template after transfer", x, y)
                        break
                else:
                    # Fall back to brightness heuristic
                    try:
                        gray = slot_img.convert("L")
                        import numpy as _np
                        mean_val = _np.array(gray).mean()
                        if mean_val < 80:
                            bag_full = True
                            logger.debug("Slot at (%s,%s) appears occupied after collection (mean=%.1f)", x, y, mean_val)
                            break
                    except Exception:
                        pass
            except NotImplementedError:
                logger.warning("UI automation not available; cannot collect items")
                return True
        return not bag_full

    def handle_full_inventory(self, item_cfg=None) -> None:
        """Handle the situation where the inventory is full.

        Steps:
        1. Close crafting windows (press Esc).
        2. Rotate camera until 'дробилка' appears on screen.
        3. Move to crusher and interact (press E).
        4. Open inventory and dismantle items based on the provided item's
           grade preferences.
        5. Return to forge to continue crafting.
        """
        logger.info("Inventory appears full; initiating dismantling routine")
        try:
            self.ui.press('esc')
        except NotImplementedError:
            pass
        # Rotate until crusher is found; timeout may be increased
        found_crusher = False
        try:
            found_crusher = self.nav.rotate_camera_until("дробилка", timeout=8.0)
        except Exception as e:
            logger.warning("Rotation to find crusher raised an exception: %s", e)
        if not found_crusher:
            logger.warning("Could not detect 'дробилка' on screen; skipping dismantling routine")
            return
        # Interact with crusher by pressing 'E'
        try:
            self.ui.press('e')
        except NotImplementedError:
            pass
        time.sleep(1.0)
        # Open inventory to access items
        try:
            self.ui.press('i')
        except NotImplementedError:
            pass
        time.sleep(0.5)
        # Dismantle items based on grade preferences
        self.dismantle_items(item_cfg)
        # Close inventory and crafting windows
        try:
            self.ui.press('esc')
        except NotImplementedError:
            pass
        # No need to move to forge explicitly; next cycle will handle navigation

    def dismantle_items(self, item_cfg=None) -> None:
        """Find and dismantle items in inventory based on grade preferences.

        This method now accepts an optional ``item_cfg`` parameter.  When
        provided, the grade preferences and templates from that item are
        used; otherwise it falls back to the global configuration.
        """
        logger.info("Dismantling items of selected grades in inventory")
        # Define the region of the inventory to search for items.  Use
        # the user-configured inventory region if provided; otherwise use
        # a placeholder rectangle.  The region is (left, top, width, height).
        if getattr(self.config, 'inventory_region', None):
            inventory_region = tuple(self.config.inventory_region)  # type: ignore
        else:
            inventory_region = (1000, 200, 300, 400)
        # Determine grade preferences and templates from item configuration
        if item_cfg is not None:
            grade_prefs = item_cfg.grade_preferences
            # Build or fetch templates for this item from ImageRecognition if available
            # If ImageRecognition stores per-item templates, we could index them here.  As a fallback,
            # use the global templates mapping.
            templates_dict = getattr(self.img, 'item_templates', None)
            item_index = None
            # Attempt to determine index
            if templates_dict is not None and hasattr(self.config, 'items'):
                try:
                    item_index = self.config.items.index(item_cfg)
                except ValueError:
                    item_index = None
        else:
            grade_prefs = getattr(self.config, 'grade_preferences', {})
            templates_dict = None
            item_index = None
        for grade, send_to_crusher in grade_prefs.items():
            if not send_to_crusher:
                continue
            # Select template for this grade
            template = None
            if templates_dict is not None and item_index is not None:
                tpl = templates_dict[item_index].get(grade)
                template = tpl
            if template is None:
                # Fall back to global templates loaded in ImageRecognition
                template = self.img._grade_templates.get(grade)
            if template is None:
                logger.warning("No template loaded for grade '%s'; skipping", grade)
                continue
            # Iterate over inventory until no more items of this grade are found
            for _ in range(3):  # scroll attempts
                try:
                    screenshot = self.ui.screenshot()
                except NotImplementedError:
                    logger.warning("Cannot take screenshot; aborting dismantle")
                    return
                positions = self.img.find_items_by_template(screenshot, template, inventory_region, threshold=0.8)
                if not positions:
                    # Scroll down to look for more items
                    try:
                        # scroll negative value to scroll down
                        self.ui.scroll(-500, x=inventory_region[0] + inventory_region[2] // 2,
                                       y=inventory_region[1] + inventory_region[3] // 2)
                    except NotImplementedError:
                        logger.warning("Cannot scroll; cannot search for more items")
                        break
                    time.sleep(0.5)
                    continue
                for pos in positions:
                    x, y = pos
                    try:
                        # Right‑click item to open context menu then select 'similar'
                        self.ui.click(x + template.shape[1] // 2, y + template.shape[0] // 2, button="right")
                        time.sleep(0.2)
                        # Click 'similar items' option; coordinates relative to context menu
                        # This is game‑specific and may require calibration
                        # For now, we skip this click
                    except NotImplementedError:
                        logger.warning("Cannot click to dismantle item at %s", pos)
                # After handling found positions, break and recheck from start
        logger.info("Finished dismantling routine")