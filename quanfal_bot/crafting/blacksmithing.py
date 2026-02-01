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
        logger.info("Starting blacksmithing cycle for %s", self.config.craft_item_name)
        # 1. Move to forge
        self.nav.move_to_station("forge")
        time.sleep(1.0)
        # 2. Open crafting interface (game‑specific: may require pressing a hotkey)
        self.open_crafting_interface()
        # 3. Select recipe
        self.select_recipe(self.config.craft_item_name)
        # 4. Initiate crafting
        self.start_craft()
        # 5. Collect items from output slots until bag is full
        while True:
            if not self.collect_items_from_output():
                # If items remain in output after collection, we assume bag is full
                self.handle_full_inventory()
                break
            # Continue crafting next batch if output was cleared successfully
            time.sleep(0.5)
            # Optionally click "Создать" again
            self.start_craft()

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

    def select_recipe(self, item_name: str) -> None:
        """Select the recipe corresponding to ``item_name`` in the crafting menu.

        Typically the recipe list is on the left side of the crafting
        window.  We type into the search box and select the first result.
        """
        logger.info("Selecting recipe '%s'", item_name)
        try:
            # Click on search field (coordinates need to be calibrated)
            search_field_coords: Tuple[int, int] = (200, 150)
            self.ui.click(*search_field_coords, button="left")
            time.sleep(0.2)
            # Type the item name
            for ch in item_name:
                self.ui.press(ch)
                time.sleep(0.05)
            time.sleep(0.2)
            # Press Enter or click on the first result (game‑specific)
            self.ui.press('enter')
        except NotImplementedError:
            logger.warning("UI automation not implemented; cannot select recipe")

    def start_craft(self) -> None:
        """Locate and click the 'Создать' button to start crafting."""
        logger.info("Attempting to start crafting")
        try:
            # Take screenshot and find 'create' button
            screenshot = self.ui.screenshot()
        except NotImplementedError:
            logger.warning("Cannot take screenshot; assuming craft started")
            return
        # Template(s) for 'Создать' can be provided in config.grade_icons
        # or another config section; here we just reuse grade_icons for example.
        templates = {"create": path for name, path in self.config.grade_icons.items() if name == "создать"}
        if not templates:
            # Without explicit templates we cannot locate button reliably
            logger.debug("No templates provided for 'Создать'; falling back to keyboard")
            try:
                self.ui.press('c')  # assume 'c' is a shortcut for crafting
            except NotImplementedError:
                pass
            return
        pos = self.img.locate_button(screenshot, "create", templates, threshold=0.8)
        if pos:
            x, y = pos
            # Adjust offset to centre of button (optional)
            self.ui.click(x + 10, y + 10, button="left")
            logger.debug("Clicked 'Создать' at %s", pos)
        else:
            logger.warning("Could not find 'Создать' button on screen")

    def collect_items_from_output(self) -> bool:
        """Collect items from crafting output slots.

        Returns True if output was successfully emptied, False if items
        remained after collection (indicating that the inventory is full).
        """
        logger.info("Collecting items from output slots")
        # Coordinates of output slots should be configured; here we use placeholder list
        output_slots: List[Tuple[int, int]] = [
            (800, 350), (850, 350), (900, 350),
            (800, 400), (850, 400), (900, 400),
        ]
        bag_full = False
        for (x, y) in output_slots:
            try:
                # Right‑click to move item to bag
                self.ui.click(x, y, button="right")
                time.sleep(0.2)
                # Optionally, we could check if the item disappeared by taking a small screenshot
            except NotImplementedError:
                logger.warning("UI automation not available; cannot collect items")
                return True
        # To determine if items remained, we could sample pixel colours
        # of the output slots and see if they are empty.  Here we simply
        # return True (output cleared) as a placeholder.
        return not bag_full

    def handle_full_inventory(self) -> None:
        """Handle the situation where the inventory is full.

        Steps:
        1. Close crafting windows (press Esc).
        2. Rotate camera until 'дробилка' appears on screen.
        3. Move to crusher and interact (press E).
        4. Open inventory and dismantle items based on grade preferences.
        5. Return to forge to continue crafting.
        """
        logger.info("Inventory appears full; initiating dismantling routine")
        try:
            self.ui.press('esc')
        except NotImplementedError:
            pass
        # Rotate until crusher is found; timeout may be increased
        found = self.nav.rotate_camera_until("дробилка", timeout=8.0)
        # Move to crusher regardless
        self.nav.move_to_station("crusher")
        # Interact with crusher (press E)
        try:
            self.ui.press('e')
        except NotImplementedError:
            pass
        time.sleep(1.0)
        # Open inventory
        try:
            self.ui.press('i')
        except NotImplementedError:
            pass
        time.sleep(0.5)
        # Dismantle items
        self.dismantle_items()
        # Close all windows and return to forge
        try:
            self.ui.press('esc')
        except NotImplementedError:
            pass
        self.nav.move_to_station("forge")

    def dismantle_items(self) -> None:
        """Find and dismantle items in inventory based on grade preferences."""
        logger.info("Dismantling items of selected grades in inventory")
        # Define the region of the inventory to search for items.  In the
        # user's description, the player marks the inventory region
        # (highlighting).  Here we use a placeholder rectangle covering
        # a portion of the screen.  Adjust these coordinates to match
        # your client: (left, top, width, height)
        inventory_region = (1000, 200, 300, 400)
        # Identify which grade templates to look for
        for grade, send_to_crusher in self.config.grade_preferences.items():
            if not send_to_crusher:
                continue
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