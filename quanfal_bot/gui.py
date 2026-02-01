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
class BotConfig:
    """Dataclass representing all configurable options for the bot."""

    # Name of item to craft
    craft_item_name: str = "Простой топор"
    # Which grades should be placed into the crusher after crafting
    grade_preferences: Dict[str, bool] = field(default_factory=lambda: {
        "серый": False,
        "зелёный": True,
        "синий": True,
        "фиолетовый": True,
        "жёлтый": True,
    })
    # Mapping from profession names to whether they are enabled
    professions_enabled: Dict[str, bool] = field(default_factory=lambda: {
        "blacksmithing": True,
        "jeweling": False,
        "tailoring": False,
    })
    # Order in which professions should be executed
    professions_order: List[str] = field(default_factory=lambda: ["blacksmithing", "jeweling", "tailoring"])
    # Paths to PNG images representing the crafted item at different grades
    grade_icons: Dict[str, str] = field(default_factory=lambda: {
        "серый": "",
        "зелёный": "",
        "синий": "",
        "фиолетовый": "",
        "жёлтый": "",
    })
    # Delay (in seconds) between runs of different modules
    cycle_delay: float = 3.0

    def to_file(self, path: str) -> None:
        """Serialize configuration to YAML file."""
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(dataclasses.asdict(self), f, allow_unicode=True)

    @classmethod
    def from_file(cls, path: str) -> "BotConfig":
        """Load configuration from YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # Merge default structure with loaded values
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
        return cls(**default_dict)  # type: ignore[arg-type]


class BotConfigGUI:
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