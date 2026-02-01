"""
Graphical user interface for configuring the Quanfal bot.

The GUI is built using Tkinter and provides a simple form where the
user can:

* Enter the name of the item to craft (e.g. "Простой топор").
* Select which grades of crafted items should be sent to the
  crusher/dismantler (серый, зелёный, синий, фиолетовый, жёлтый).
* Enable or disable individual crafting professions.
* Choose the order in which professions are executed.
* Attach PNG images representing the appearance of the crafted item
  at different grades.  These images are used by the image
  recognition module to identify items in the inventory.

The configuration is persisted as a YAML file via methods on the
``BotConfig`` dataclass.

Note: Tkinter may not be installed in all Python environments.
Running the GUI requires ``tkinter`` to be available.  If you cannot
launch the GUI due to missing dependencies, you can still edit the
configuration file manually or set the fields directly in code.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yaml  # PyYAML is part of this environment

try:
    import tkinter as tk
    from tkinter import filedialog, ttk, messagebox
except ImportError:
    tk = None  # type: ignore


@dataclass
class ItemConfig:
    """Configuration for a single craftable item.

    Each item has its own name, grade preferences and grade icon paths.
    """
    craft_item_name: str = "Простой топор"
    grade_preferences: Dict[str, bool] = field(default_factory=lambda: {
        "серый": False,
        "зелёный": True,
        "синий": True,
        "фиолетовый": True,
        "жёлтый": True,
    })
    grade_icons: Dict[str, str] = field(default_factory=lambda: {
        "серый": "",
        "зелёный": "",
        "синий": "",
        "фиолетовый": "",
        "жёлтый": "",
    })
    # Additional trigger images for this item.  These allow the bot to
    # locate UI elements via template matching instead of relying on OCR.
    # Supported keys:
    #   item: template of the recipe/item name in the crafting list
    #   create: template of the "Создать" button
    #   empty_slot: template of an empty crafting output slot
    #   inventory_slot: template of an empty inventory slot
    triggers: Dict[str, str] = field(default_factory=lambda: {
        "item": "",
        "create": "",
        "empty_slot": "",
        "inventory_slot": "",
    })


@dataclass
class BotConfig:
    """Dataclass representing all configurable options for the bot.

    In the multi‑item version, configuration is organised around a list of
    ``ItemConfig`` objects.  Each item can have its own grade
    preferences and icons.  The order of crafting professions and the
    enabled state of professions remain global settings.
    """
    # List of item configurations
    items: List[ItemConfig] = field(default_factory=lambda: [ItemConfig()])
    # Mapping from profession names to whether they are enabled
    professions_enabled: Dict[str, bool] = field(default_factory=lambda: {
        "blacksmithing": True,
        "jeweling": False,
        "tailoring": False,
    })
    # Order in which professions should be executed
    professions_order: List[str] = field(default_factory=lambda: ["blacksmithing", "jeweling", "tailoring"])
    # Delay (in seconds) between runs of different modules
    cycle_delay: float = 3.0
    # Region of the crafting window containing output slots (left, top, width, height)
    # This is used to detect empty or filled slots and should be calibrated in the GUI.
    craft_window_region: Optional[List[int]] = None
    # Region of the inventory where items are displayed (left, top, width, height)
    inventory_region: Optional[List[int]] = None

    def to_file(self, path: str) -> None:
        """Serialize configuration to YAML file."""
        # Convert dataclasses to serialisable dictionaries
        data = dataclasses.asdict(self)
        # dataclasses.asdict already converts nested dataclasses
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True)

    @classmethod
    def from_file(cls, path: str) -> "BotConfig":
        """Load configuration from YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # Build default instance
        default = cls()
        default_dict = dataclasses.asdict(default)
        # Deep merge dictionaries
        def merge(dflt, src):
            for key, value in src.items():
                if isinstance(value, dict) and isinstance(dflt.get(key), dict):
                    merge(dflt[key], value)
                else:
                    dflt[key] = value
        merge(default_dict, data)
        # Recreate ItemConfig objects from dictionaries
        items_data = default_dict.get("items", [])
        items: List[ItemConfig] = []
        for item in items_data:
            # Convert dictionaries back to ItemConfig
            items.append(ItemConfig(**item))
        default_dict["items"] = items
        # Build BotConfig instance
        cfg = cls()
        for k, v in default_dict.items():
            setattr(cfg, k, v)
        return cfg


class SingleItemBotConfigGUI:
    """Simple Tkinter-based GUI for editing ``BotConfig`` objects."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.result: Optional[BotConfig] = None

        if tk is None:
            raise RuntimeError("Tkinter is not available in this environment. The GUI cannot be launched.")

        # Create main window
        self.root = tk.Tk()
        self.root.title("Настройка бота Quanfal")
        self.root.geometry("600x500")

        # Craft item name
        tk.Label(self.root, text="Название предмета для крафта:").pack(anchor="w", padx=10, pady=(10, 0))
        self.craft_name_var = tk.StringVar(value=self.config.craft_item_name)
        tk.Entry(self.root, textvariable=self.craft_name_var, width=40).pack(anchor="w", padx=10, pady=(0, 10))

        # Grade preferences
        tk.Label(self.root, text="Грейды для помещения в дробилку:").pack(anchor="w", padx=10)
        self.grade_vars: Dict[str, tk.BooleanVar] = {}
        grade_frame = tk.Frame(self.root)
        grade_frame.pack(anchor="w", padx=20, pady=(0, 10))
        for grade, selected in self.config.grade_preferences.items():
            var = tk.BooleanVar(value=selected)
            self.grade_vars[grade] = var
            cb = tk.Checkbutton(grade_frame, text=grade, variable=var)
            cb.pack(side="left", padx=5)

        # Profession toggles
        tk.Label(self.root, text="Включить профессии:").pack(anchor="w", padx=10)
        self.profession_vars: Dict[str, tk.BooleanVar] = {}
        prof_frame = tk.Frame(self.root)
        prof_frame.pack(anchor="w", padx=20, pady=(0, 10))
        for prof, enabled in self.config.professions_enabled.items():
            var = tk.BooleanVar(value=enabled)
            self.profession_vars[prof] = var
            cb = tk.Checkbutton(prof_frame, text=prof, variable=var)
            cb.pack(side="left", padx=5)

        # Grade icons selection
        tk.Label(self.root, text="Иконки для предмета по грейдам (PNG):").pack(anchor="w", padx=10)
        icon_frame = tk.Frame(self.root)
        icon_frame.pack(anchor="w", padx=20, pady=(0, 10))
        self.icon_vars: Dict[str, tk.StringVar] = {}
        for grade, path in self.config.grade_icons.items():
            row = tk.Frame(icon_frame)
            row.pack(anchor="w")
            tk.Label(row, text=f"{grade}: ").pack(side="left")
            var = tk.StringVar(value=path)
            self.icon_vars[grade] = var
            entry = tk.Entry(row, textvariable=var, width=30)
            entry.pack(side="left")
            def browse(grade=grade):  # default arg to capture current grade
                filename = filedialog.askopenfilename(filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
                if filename:
                    self.icon_vars[grade].set(filename)
            btn = tk.Button(row, text="Обзор...", command=browse)
            btn.pack(side="left")

        # Profession order
        tk.Label(self.root, text="Порядок выполнения профессий:").pack(anchor="w", padx=10)
        self.order_listbox = tk.Listbox(self.root, selectmode=tk.MULTIPLE)
        for prof in self.config.professions_order:
            self.order_listbox.insert(tk.END, prof)
        self.order_listbox.pack(anchor="w", padx=20, pady=(0, 10))
        # Buttons to move items up and down
        order_btn_frame = tk.Frame(self.root)
        order_btn_frame.pack(anchor="w", padx=20, pady=(0, 10))
        tk.Button(order_btn_frame, text="↑", command=self._move_up).pack(side="left")
        tk.Button(order_btn_frame, text="↓", command=self._move_down).pack(side="left")

        # Cycle delay
        tk.Label(self.root, text="Задержка между циклами (с):").pack(anchor="w", padx=10)
        self.delay_var = tk.DoubleVar(value=self.config.cycle_delay)
        tk.Spinbox(self.root, textvariable=self.delay_var, from_=0.5, to=60.0, increment=0.5, width=5).pack(anchor="w", padx=20, pady=(0, 10))

        # Save and cancel buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Сохранить", command=self._on_save).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Отмена", command=self._on_cancel).pack(side="left", padx=5)

    def _move_up(self) -> None:
        sel = list(self.order_listbox.curselection())
        if not sel:
            return
        for index in sel:
            if index == 0:
                continue
            value = self.order_listbox.get(index)
            self.order_listbox.delete(index)
            self.order_listbox.insert(index - 1, value)
            self.order_listbox.selection_set(index - 1)

    def _move_down(self) -> None:
        sel = list(self.order_listbox.curselection())[::-1]
        if not sel:
            return
        for index in sel:
            if index == self.order_listbox.size() - 1:
                continue
            value = self.order_listbox.get(index)
            self.order_listbox.delete(index)
            self.order_listbox.insert(index + 1, value)
            self.order_listbox.selection_set(index + 1)

    def _on_save(self) -> None:
        # Collect values from form into new config
        new_config = BotConfig()
        new_config.craft_item_name = self.craft_name_var.get().strip()
        new_config.grade_preferences = {grade: var.get() for grade, var in self.grade_vars.items()}
        new_config.professions_enabled = {prof: var.get() for prof, var in self.profession_vars.items()}
        new_config.grade_icons = {grade: var.get().strip() for grade, var in self.icon_vars.items()}
        new_config.cycle_delay = float(self.delay_var.get())
        # Order list
        new_config.professions_order = list(self.order_listbox.get(0, tk.END))
        # Validate: ensure craft name is not empty
        if not new_config.craft_item_name:
            messagebox.showerror("Ошибка", "Название предмета для крафта не может быть пустым.")
            return
        self.result = new_config
        self.root.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.root.destroy()

    def run(self) -> Optional[BotConfig]:
        """Launch the GUI and block until the user closes it.

        Returns
        -------
        BotConfig or None
            The updated configuration if the user clicked Save, or
            ``None`` if the dialog was cancelled.
        """
        self.root.mainloop()
        return self.result


# -----------------------------------------------------------------------------
# Multi‑item GUI
# -----------------------------------------------------------------------------

class BotConfigGUI:
    """Tkinter-based GUI for editing ``BotConfig`` objects with multi-item support.

    This GUI allows users to configure multiple craftable items, each with its
    own grade preferences and grade icon paths.  Items can be added or removed,
    and the global crafting professions and their order can be customised.
    """

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.result: Optional[BotConfig] = None

        if tk is None:
            raise RuntimeError("Tkinter is not available in this environment. The GUI cannot be launched.")

        # Create main window
        self.root = tk.Tk()
        self.root.title("Настройка бота Quanfal")
        self.root.geometry("700x600")

        # Section for managing multiple items
        tk.Label(self.root, text="Предметы для крафта:").pack(anchor="w", padx=10, pady=(10, 0))
        items_frame = tk.Frame(self.root)
        items_frame.pack(anchor="w", padx=10, pady=(0, 10), fill="x")
        self.item_listbox = tk.Listbox(items_frame, height=5)
        self.item_listbox.pack(side="left", fill="x", expand=True)
        # Populate listbox with current items
        for item in self.config.items:
            self.item_listbox.insert(tk.END, item.craft_item_name)
        # Buttons to add and remove items
        item_btn_frame = tk.Frame(items_frame)
        item_btn_frame.pack(side="left", padx=5)
        tk.Button(item_btn_frame, text="+", width=3, command=self._add_item).pack(pady=2)
        tk.Button(item_btn_frame, text="-", width=3, command=self._remove_item).pack(pady=2)
        # Bind selection event
        self.item_listbox.bind("<<ListboxSelect>>", self._on_item_select)

        # Editor frame for selected item
        self.editor_frame = tk.Frame(self.root)
        self.editor_frame.pack(anchor="w", fill="x", padx=10, pady=(0, 10))
        # Create variables for item fields (will be bound to current item)
        self.craft_name_var = tk.StringVar()
        self.grade_vars: Dict[str, tk.BooleanVar] = {}
        self.icon_vars: Dict[str, tk.StringVar] = {}
        # Build editor UI
        self._build_item_editor()

        # Profession toggles (global)
        tk.Label(self.root, text="Включить профессии:").pack(anchor="w", padx=10)
        self.profession_vars: Dict[str, tk.BooleanVar] = {}
        prof_frame = tk.Frame(self.root)
        prof_frame.pack(anchor="w", padx=20, pady=(0, 10))
        for prof, enabled in self.config.professions_enabled.items():
            var = tk.BooleanVar(value=enabled)
            self.profession_vars[prof] = var
            cb = tk.Checkbutton(prof_frame, text=prof, variable=var)
            cb.pack(side="left", padx=5)

        # Profession order
        tk.Label(self.root, text="Порядок выполнения профессий:").pack(anchor="w", padx=10)
        self.order_listbox = tk.Listbox(self.root, selectmode=tk.MULTIPLE)
        for prof in self.config.professions_order:
            self.order_listbox.insert(tk.END, prof)
        self.order_listbox.pack(anchor="w", padx=20, pady=(0, 10))
        # Buttons to move items up and down
        order_btn_frame = tk.Frame(self.root)
        order_btn_frame.pack(anchor="w", padx=20, pady=(0, 10))
        tk.Button(order_btn_frame, text="↑", command=self._move_up).pack(side="left")
        tk.Button(order_btn_frame, text="↓", command=self._move_down).pack(side="left")

        # Cycle delay
        tk.Label(self.root, text="Задержка между циклами (с):").pack(anchor="w", padx=10)
        self.delay_var = tk.DoubleVar(value=self.config.cycle_delay)
        tk.Spinbox(self.root, textvariable=self.delay_var, from_=0.5, to=60.0, increment=0.5, width=5).pack(anchor="w", padx=20, pady=(0, 10))

        # Save and cancel buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Сохранить", command=self._on_save).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Отмена", command=self._on_cancel).pack(side="left", padx=5)

        # Select first item by default
        if self.config.items:
            self.item_listbox.selection_set(0)
            self._load_item(0)

    # ---- Multi-item management ----
    def _build_item_editor(self) -> None:
        """Construct the item editor UI inside ``self.editor_frame``."""
        for widget in self.editor_frame.winfo_children():
            widget.destroy()
        # Item name
        tk.Label(self.editor_frame, text="Название предмета:").pack(anchor="w")
        tk.Entry(self.editor_frame, textvariable=self.craft_name_var, width=40).pack(anchor="w", pady=(0, 5))
        # Grade preferences
        tk.Label(self.editor_frame, text="Грейды для помещения в дробилку:").pack(anchor="w")
        grade_frame = tk.Frame(self.editor_frame)
        grade_frame.pack(anchor="w", padx=10, pady=(0, 5))
        # Reset grade vars
        self.grade_vars.clear()
        for grade in ["серый", "зелёный", "синий", "фиолетовый", "жёлтый"]:
            var = tk.BooleanVar(value=False)
            self.grade_vars[grade] = var
            cb = tk.Checkbutton(grade_frame, text=grade, variable=var)
            cb.pack(side="left", padx=5)
        # Grade icons selection
        tk.Label(self.editor_frame, text="Иконки для предмета по грейдам (PNG):").pack(anchor="w")
        icon_frame = tk.Frame(self.editor_frame)
        icon_frame.pack(anchor="w", padx=10, pady=(0, 5))
        # Reset icon vars
        self.icon_vars.clear()
        for grade in ["серый", "зелёный", "синий", "фиолетовый", "жёлтый"]:
            row = tk.Frame(icon_frame)
            row.pack(anchor="w")
            tk.Label(row, text=f"{grade}: ").pack(side="left")
            var = tk.StringVar(value="")
            self.icon_vars[grade] = var
            entry = tk.Entry(row, textvariable=var, width=30)
            entry.pack(side="left")
            def browse(path_var=var):
                filename = filedialog.askopenfilename(filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
                if filename:
                    path_var.set(filename)
            btn = tk.Button(row, text="Обзор...", command=browse)
            btn.pack(side="left")

    def _add_item(self) -> None:
        """Add a new item configuration to the list."""
        # Save current item before switching
        self._save_current_item()
        new_item = ItemConfig()
        self.config.items.append(new_item)
        self.item_listbox.insert(tk.END, new_item.craft_item_name)
        # Select the new item
        index = self.item_listbox.size() - 1
        self.item_listbox.selection_clear(0, tk.END)
        self.item_listbox.selection_set(index)
        self._load_item(index)

    def _remove_item(self) -> None:
        """Remove the selected item configuration if more than one exists."""
        selection = list(self.item_listbox.curselection())
        if not selection:
            return
        idx = selection[0]
        if len(self.config.items) <= 1:
            # Do not remove the last item
            return
        # Remove from config and listbox
        self.config.items.pop(idx)
        self.item_listbox.delete(idx)
        # Select another item
        new_idx = min(idx, len(self.config.items) - 1)
        self.item_listbox.selection_clear(0, tk.END)
        self.item_listbox.selection_set(new_idx)
        self._load_item(new_idx)

    def _on_item_select(self, event) -> None:
        """Handler for selecting an item in the listbox."""
        selection = list(self.item_listbox.curselection())
        if not selection:
            return
        # Save previous item before switching
        self._save_current_item()
        idx = selection[0]
        self._load_item(idx)

    def _load_item(self, idx: int) -> None:
        """Load item at ``idx`` into the editor fields."""
        item = self.config.items[idx]
        # Update variables
        self.craft_name_var.set(item.craft_item_name)
        for grade in self.grade_vars:
            self.grade_vars[grade].set(item.grade_preferences.get(grade, False))
        for grade in self.icon_vars:
            self.icon_vars[grade].set(item.grade_icons.get(grade, ""))
        # Update the listbox entry to reflect name change
        self.item_listbox.delete(idx)
        self.item_listbox.insert(idx, item.craft_item_name)
        # Ensure selection
        self.item_listbox.selection_clear(0, tk.END)
        self.item_listbox.selection_set(idx)

    def _save_current_item(self) -> None:
        """Persist the current editor fields into the selected item."""
        selection = list(self.item_listbox.curselection())
        if not selection:
            return
        idx = selection[0]
        item = self.config.items[idx]
        item.craft_item_name = self.craft_name_var.get().strip()
        item.grade_preferences = {grade: var.get() for grade, var in self.grade_vars.items()}
        item.grade_icons = {grade: var.get().strip() for grade, var in self.icon_vars.items()}
        # Update the listbox entry to reflect name change
        self.item_listbox.delete(idx)
        self.item_listbox.insert(idx, item.craft_item_name)
        self.item_listbox.selection_clear(0, tk.END)
        self.item_listbox.selection_set(idx)

    def _move_up(self) -> None:
        sel = list(self.order_listbox.curselection())
        if not sel:
            return
        for index in sel:
            if index == 0:
                continue
            value = self.order_listbox.get(index)
            self.order_listbox.delete(index)
            self.order_listbox.insert(index - 1, value)
            self.order_listbox.selection_set(index - 1)

    def _move_down(self) -> None:
        sel = list(self.order_listbox.curselection())[::-1]
        if not sel:
            return
        for index in sel:
            if index == self.order_listbox.size() - 1:
                continue
            value = self.order_listbox.get(index)
            self.order_listbox.delete(index)
            self.order_listbox.insert(index + 1, value)
            self.order_listbox.selection_set(index + 1)

    def _on_save(self) -> None:
        # Save current item first
        self._save_current_item()
        # Construct new config to return
        new_config = BotConfig()
        # Deep copy items
        new_config.items = [dataclasses.replace(item) for item in self.config.items]
        new_config.professions_enabled = {prof: var.get() for prof, var in self.profession_vars.items()}
        new_config.professions_order = list(self.order_listbox.get(0, tk.END))
        new_config.cycle_delay = float(self.delay_var.get())
        # Validate: ensure all item names are non-empty
        for item in new_config.items:
            if not item.craft_item_name:
                messagebox.showerror("Ошибка", "Название предмета не может быть пустым.")
                return
        self.result = new_config
        self.root.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.root.destroy()

    def run(self) -> Optional[BotConfig]:
        """Launch the GUI and block until the user closes it.

        Returns
        -------
        BotConfig or None
            The updated configuration if the user clicked Save, or
            ``None`` if the dialog was cancelled.
        """
        self.root.mainloop()
        return self.result