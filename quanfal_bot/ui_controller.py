"""
UIController abstracts away low‑level control of the keyboard and mouse.

This module provides a simple wrapper around pyautogui (if available) to
send mouse clicks, move the cursor, scroll the mouse wheel and send
keystrokes.  These methods include basic logging and error handling to
make it easier to debug the automation.  If pyautogui is not
installed, the methods will raise ``NotImplementedError`` to avoid
silent failures.
"""

from __future__ import annotations

import logging
from typing import Tuple, Optional
import time

logger = logging.getLogger(__name__)

try:
    import pyautogui
    _has_pyautogui = True
except ImportError:
    pyautogui = None  # type: ignore
    _has_pyautogui = False


class UIController:
    """Abstraction for mouse/keyboard automation."""

    def __init__(self, stop_event: Optional[object] = None, pause_event: Optional[object] = None) -> None:
        """Initialize the UIController.

        Parameters
        ----------
        stop_event: threading.Event or similar
            When set, all UI actions will raise a ``RuntimeError`` to stop the bot.
        pause_event: threading.Event or similar
            When set, UI actions will block until cleared.  Useful for pausing the bot.
        """
        if not _has_pyautogui:
            logger.warning(
                "pyautogui is not available; UI automation functions will not work. "
                "Install pyautogui to enable automation."
            )
        self.stop_event = stop_event
        self.pause_event = pause_event

    def _guard(self) -> None:
        """Check for stop or pause state before performing an action.

        Raises
        ------
        RuntimeError
            If the ``stop_event`` is set.
        """
        # If a stop event is set, raise to terminate loops
        if self.stop_event is not None:
            try:
                if self.stop_event.is_set():
                    raise RuntimeError("Bot stopped")
            except AttributeError:
                # Generic objects may not have is_set
                pass
        # If a pause event is set, wait until cleared
        if self.pause_event is not None:
            try:
                while self.pause_event.is_set():
                    # If stop is requested during pause, break
                    if self.stop_event is not None and self.stop_event.is_set():
                        raise RuntimeError("Bot stopped during pause")
                    time.sleep(0.05)
            except AttributeError:
                pass

    # Mouse methods
    def click(self, x: int, y: int, button: str = "left") -> None:
        """Click at the specified screen coordinates.

        Parameters
        ----------
        x, y: int
            Screen coordinates.
        button: str
            Either "left" or "right".
        """
        if not _has_pyautogui:
            raise NotImplementedError("pyautogui is required for click()")
        self._guard()
        logger.debug("Clicking at (%s, %s) with button %s", x, y, button)
        pyautogui.click(x=x, y=y, button=button)

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None:
        """Move the mouse to the specified screen coordinates.

        duration controls how long the movement should take.
        """
        if not _has_pyautogui:
            raise NotImplementedError("pyautogui is required for move_to()")
        self._guard()
        logger.debug("Moving mouse to (%s, %s) over %s seconds", x, y, duration)
        pyautogui.moveTo(x, y, duration=duration)

    def drag_rel(self, dx: int, dy: int, duration: float = 0.1, button: str = "left") -> None:
        """Drag mouse relative to current position. Useful for camera rotation.

        Parameters
        ----------
        dx, dy: int
            Relative movement in pixels.
        duration: float
            Duration of the drag.
        button: str
            Mouse button to hold during drag.
        """
        if not _has_pyautogui:
            raise NotImplementedError("pyautogui is required for drag_rel()")
        self._guard()
        logger.debug("Dragging relative by (%s, %s) over %s seconds with button %s", dx, dy, duration, button)
        pyautogui.dragRel(dx, dy, duration=duration, button=button)

    def scroll(self, clicks: int, x: int | None = None, y: int | None = None) -> None:
        """Scroll the mouse wheel.

        A positive value scrolls up, negative scrolls down.  x and y
        parameters can be used to specify where the scroll event should
        occur, otherwise it happens at the current cursor position.
        """
        if not _has_pyautogui:
            raise NotImplementedError("pyautogui is required for scroll()")
        self._guard()
        logger.debug("Scrolling %s clicks at (%s, %s)", clicks, x, y)
        if x is not None and y is not None:
            pyautogui.scroll(clicks, x=x, y=y)
        else:
            pyautogui.scroll(clicks)

    # Keyboard methods
    def press(self, key: str) -> None:
        """Press a single key."""
        if not _has_pyautogui:
            raise NotImplementedError("pyautogui is required for press()")
        self._guard()
        logger.debug("Pressing key %s", key)
        pyautogui.press(key)

    def hotkey(self, *keys: str) -> None:
        """Press a combination of keys."""
        if not _has_pyautogui:
            raise NotImplementedError("pyautogui is required for hotkey()")
        self._guard()
        logger.debug("Pressing hotkey %s", keys)
        pyautogui.hotkey(*keys)

    # Screen capture
    def screenshot(self, region: Tuple[int, int, int, int] | None = None):
        """Take a screenshot of the entire screen or a region.

        region: (left, top, width, height)
        Returns a PIL Image object if pyautogui is available, otherwise
        raises NotImplementedError.
        """
        if not _has_pyautogui:
            raise NotImplementedError("pyautogui is required for screenshot()")
        self._guard()
        logger.debug("Taking screenshot of region %s", region)
        return pyautogui.screenshot(region=region)