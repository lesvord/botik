"""
Core orchestration for the Quanfal crafting bot.

This module provides an entrypoint for running the bot.  It loads
configuration via the GUI, instantiates the appropriate crafting
modules and runs them in a loop.  The bot is designed to be modular
and easily extendable: new crafting modules can be plugged in by
adding them to the ``crafting`` package and registering them in
``available_modules`` below.

The actual low‑level automation (mouse, keyboard and image
recognition) is delegated to helper modules.  In production you
would replace the stubs in ``ui_controller`` and ``image_recognition``
with concrete implementations using libraries such as PyAutoGUI,
OpenCV and pytesseract.  See documentation in those modules for
guidance.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import time
import threading
from typing import Dict, List, Optional, Type

from .gui import BotConfigGUI, BotConfig
from .navigation import Navigation
from .ui_controller import UIController
from .image_recognition import ImageRecognition

from .crafting.base import CraftingModule

# import crafting modules here.  They will automatically register
# themselves as subclasses of CraftingModule.  You can add more
# professions by placing a new module under ``quanfal_bot/crafting``.
from .crafting.blacksmithing import Blacksmithing
from .crafting.jeweling import Jeweling
from .crafting.tailoring import Tailoring


logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> BotConfig:
    """Load bot configuration from YAML/JSON file.

    If the file does not exist or cannot be parsed, a default
    configuration is returned.

    Parameters
    ----------
    config_path: Path
        Path to the configuration file on disk.

    Returns
    -------
    BotConfig
        Parsed configuration object.
    """
    if not config_path.exists():
        logger.info("Configuration file %s not found, using defaults", config_path)
        return BotConfig()

    try:
        return BotConfig.from_file(config_path)
    except Exception as exc:
        logger.warning("Failed to load config file %s: %s", config_path, exc)
        return BotConfig()


def save_config(config: BotConfig, config_path: Path) -> None:
    """Persist the current configuration to disk.

    Parameters
    ----------
    config: BotConfig
        Configuration to save.
    config_path: Path
        Path where the configuration should be saved.
    """
    try:
        config.to_file(config_path)
        logger.info("Configuration saved to %s", config_path)
    except Exception as exc:
        logger.warning("Failed to save config to %s: %s", config_path, exc)


def instantiate_modules(config: BotConfig,
                        ui: UIController,
                        nav: Navigation,
                        img: ImageRecognition) -> List[CraftingModule]:
    """Create a list of crafting module instances based on configuration.

    Parameters
    ----------
    config: BotConfig
        User configuration specifying which professions are active.
    ui: UIController
        Controller for mouse/keyboard automation.
    nav: Navigation
        Navigation helper for moving between stations.
    img: ImageRecognition
        Image processing helper.

    Returns
    -------
    list of CraftingModule
        Instantiated crafting modules.
    """
    modules: List[CraftingModule] = []
    # Map of profession names to classes
    available: Dict[str, Type[CraftingModule]] = {
        "blacksmithing": Blacksmithing,
        "jeweling": Jeweling,
        "tailoring": Tailoring,
    }

    for prof_name in config.professions_order:
        cls = available.get(prof_name)
        if cls is None:
            logger.warning("Unknown profession '%s' in configuration", prof_name)
            continue
        if prof_name not in config.professions_enabled or not config.professions_enabled[prof_name]:
            continue
        modules.append(cls(ui, nav, img, config))
    return modules


def run_bot():
    """Main entrypoint for running the Quanfal bot.

    - Launches the configuration GUI to collect user preferences.
    - Instantiates helper objects for UI control, navigation and image
      recognition.
    - Instantiates active crafting modules.
    - Runs the modules in a loop until user interrupts the program
      (e.g. via Ctrl+C).
    """
    # Determine path for config file relative to this script
    config_path = Path(os.path.expanduser("~/.quanfal_bot_config.yaml"))
    config = load_config(config_path)

    # Launch configuration GUI
    gui = BotConfigGUI(config)
    updated_config = gui.run()
    if updated_config is not None:
        config = updated_config
        save_config(config, config_path)

    # Instantiate helpers
    # Create events to support stopping and pausing via hotkeys
    stop_event = threading.Event()
    pause_event = threading.Event()
    ui = UIController(stop_event=stop_event, pause_event=pause_event)
    img = ImageRecognition(config)
    nav = Navigation(ui, img, config)

    # Instantiate crafting modules
    modules = instantiate_modules(config, ui, nav, img)
    if not modules:
        logger.info("No crafting modules enabled; exiting.")
        return

    # Set up global hotkeys for stopping (F12) and pausing/resuming (F11)
    try:
        import keyboard  # type: ignore

        # Define actions for stop and pause
        def stop_bot():
            stop_event.set()
            logger.info("Stop hotkey pressed (F12). Finishing current action...")

        def toggle_pause():
            if pause_event.is_set():
                pause_event.clear()
                logger.info("Bot resumed (F11)")
            else:
                pause_event.set()
                logger.info("Bot paused (F11)")

        keyboard.add_hotkey('f12', stop_bot)
        keyboard.add_hotkey('f11', toggle_pause)
        logger.info("Hotkeys registered: F12 to stop, F11 to pause/resume")
    except Exception as e:
        logger.warning("Could not register hotkeys (F12/F11); stop/pause disabled: %s", e)

    logger.info("Starting bot with modules: %s", [m.__class__.__name__ for m in modules])
    try:
        # Main execution loop
        while not stop_event.is_set():
            for module in modules:
                if stop_event.is_set():
                    break
                logger.info("Executing module: %s", module)
                try:
                    module.run_cycle()
                except Exception as module_error:
                    logger.error("Error in module %s: %s", module, module_error)
                    # Continue other modules on error
                # Delay between modules
                if stop_event.is_set():
                    break
                time.sleep(config.cycle_delay)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user via KeyboardInterrupt.")
    finally:
        stop_event.set()
        logger.info("Bot exiting.")


if __name__ == "__main__":
    run_bot()