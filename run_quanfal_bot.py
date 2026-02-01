#!/usr/bin/env python3
"""
Script to launch the Quanfal crafting bot.

Run this file directly to open the GUI and start the bot.  It simply
delegates to ``quanfal_bot.core.run_bot``.
"""

from quanfal_bot.core import run_bot

if __name__ == "__main__":
    run_bot()