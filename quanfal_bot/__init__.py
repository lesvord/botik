"""
quanfal_bot package

This package contains modules for implementing a modular crafting bot
for the fantasy game *Куанфол* (Quanfal).  The bot is designed to
automate repetitive crafting tasks such as blacksmithing, jewelling
and tailoring.  Its architecture emphasises modularity and
extensibility: each profession is implemented in its own module and
can be turned on or off through configuration.

The code in this package is meant as a starting point and blueprint
rather than a finished, ready‑to‑run solution.  Some functionality
such as GUI configuration and low‑level mouse/keyboard automation
depends on external libraries (e.g. Tkinter, PyAutoGUI).  If those
libraries are not installed on your system, you may need to install
them manually or adjust the implementation to match your environment.
"""

__all__ = [
    "core",
    "gui",
    "ui_controller",
    "image_recognition",
    "navigation",
    "crafting",
]