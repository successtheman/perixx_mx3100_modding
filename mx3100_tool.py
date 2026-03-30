"""
Perixx MX-3100 Gaming Mouse Configuration Tool

A replacement for the original MX-3100 driver software that adds support
for assigning F13-F24 keys to mouse buttons.

Features:
  - Assign any keyboard key (including F13-F24) to any mouse button
  - Combo key support (Ctrl/Shift/Alt/Win + key)
  - DPI control, media keys, scroll, and other built-in actions
  - Profile management
  - Protocol sniffer for reverse-engineering

Usage:
  python mx3100_tool.py            # Launch GUI
  python mx3100_tool.py --cli      # Command-line mode
  python mx3100_tool.py --detect   # Just detect mouse

Run as Administrator for HID device access.
"""

import sys
import json
import os
import argparse
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from mx3100_hid import enumerate_devices, MX3100Device
from mx3100_protocol import (
    BUTTON_NAMES, TOTAL_BUTTONS, ACTION_NAMES, BUTTON_ENTRY_SIZE,
    BTN_TYPE_KEYBOARD, BTN_TYPE_MOUSE, BTN_TYPE_MULTIMEDIA, BTN_TYPE_DPI,
    ACTION_KEYBOARD, ACTION_MOUSE_BUTTON, ACTION_MULTIMEDIA, ACTION_DPI,
    ACTION_DISABLED, ACTION_DEFAULT,
    MOUSE_LEFT_CLICK, MOUSE_RIGHT_CLICK, MOUSE_MIDDLE_CLICK,
    MOUSE_BACK, MOUSE_FORWARD, MOUSE_SCROLL_UP, MOUSE_SCROLL_DOWN,
    DPI_PLUS, DPI_MINUS, DPI_LOOP,
    HID_KEY_NAMES, HID_NAME_TO_CODE, HID_KEY_NONE,
    HID_MOD_LCTRL, HID_MOD_LSHIFT, HID_MOD_LALT, HID_MOD_LGUI,
    HID_MOD_RCTRL, HID_MOD_RSHIFT, HID_MOD_RALT, HID_MOD_RGUI,
    MEDIA_PLAY_PAUSE, MEDIA_STOP, MEDIA_NEXT, MEDIA_PREV,
    MEDIA_VOLUME_UP, MEDIA_VOLUME_DOWN, MEDIA_MUTE,
    ButtonConfig, get_all_assignable_keys, get_function_keys,
    DEFAULT_BUTTONS,
    # Protocol constants
    CMD_MSG_LEN, DATA_LINE_LEN, SECTION_LEN,
    CONFIGS_ADDR, BUTTONS_ADDR,
    SETTINGS_ADDR_MAX, SETTINGS_ADDR_PARITY, ADDR_READ,
)

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles")


# ─── Profile persistence (JSON-based) ───────────────────────────────────────

def save_profile(filename, buttons):
    """Save button configuration to a JSON file."""
    data = {}
    for btn_idx, cfg in buttons.items():
        data[str(btn_idx)] = {
            "btn_type": cfg.btn_type,
            "modifier": cfg.modifier,
            "key_code": cfg.key_code,
            "extra": cfg.extra,
        }
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


def load_profile(filename):
    """Load button configuration from a JSON file."""
    with open(filename, "r") as f:
        data = json.load(f)
    buttons = {}
    for btn_idx_str, cfg_data in data.items():
        btn_idx = int(btn_idx_str)
        buttons[btn_idx] = ButtonConfig(
            cfg_data.get("btn_type", cfg_data.get("action_type", 0)),
            cfg_data.get("modifier", 0),
            cfg_data.get("key_code", 0),
            cfg_data.get("extra", cfg_data.get("extra1", 0)),
        )
    return buttons


# ─── HID Protocol Layer (from pzl/mx3100drv, confirmed working) ─────────────
# Protocol uses 9-byte Feature Reports for commands, and 64-byte Output/Input
# reports for data transfer. Communication is via Interface #2 (mi_02),
# UsagePage 0xFF00 (vendor-specific).
#
# Startup: Two feature report commands to initialize the mouse.
# Read: send feature cmd → read feature ACK → read 2×64 byte data
# Write: send feature cmd → write 2×64 byte data

STARTUP_CMD_1 = [0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFD]
STARTUP_CMD_2 = [0x03, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0xFA]


def send_startup(dev):
    """Send the two startup commands to initialize communication."""
    dev.send_feature(STARTUP_CMD_1)
    dev.send_feature(STARTUP_CMD_2)


def read_section(dev, addr):
    """Read a 128-byte section from mouse memory.
    Returns list of 128 bytes, or None on failure.
    """
    cmd = [0] * CMD_MSG_LEN
    cmd[7] = addr
    cmd[0] = ADDR_READ | (SETTINGS_ADDR_MAX - addr + SETTINGS_ADDR_PARITY)

    dev.send_feature(cmd)
    dev.read_feature()  # ACK

    data1 = dev.read_data()
    if data1 is None:
        return None
    data2 = dev.read_data()
    if data2 is None:
        return None
    return data1 + data2


def write_section(dev, addr, data_128bytes):
    """Write a 128-byte section to mouse memory."""
    cmd = [0] * CMD_MSG_LEN
    cmd[7] = addr
    cmd[0] = SETTINGS_ADDR_MAX - addr + SETTINGS_ADDR_PARITY
    cmd[2] = SECTION_LEN  # 128

    dev.send_feature(cmd)
    dev.write_data(data_128bytes[:DATA_LINE_LEN])
    dev.write_data(data_128bytes[DATA_LINE_LEN:SECTION_LEN])


def parse_buttons_from_section(data):
    """Parse 19 buttons from a 128-byte button section."""
    buttons = {}
    for i in range(TOTAL_BUTTONS):
        offset = i * BUTTON_ENTRY_SIZE
        if offset + BUTTON_ENTRY_SIZE <= len(data):
            cfg = ButtonConfig.from_bytes(data[offset:offset + BUTTON_ENTRY_SIZE])
            buttons[i] = cfg
    return buttons


def build_button_section(buttons):
    """Build a 128-byte section from button configs."""
    data = bytearray(SECTION_LEN)
    for btn_idx in range(TOTAL_BUTTONS):
        cfg = buttons.get(btn_idx, ButtonConfig.disabled())
        offset = btn_idx * BUTTON_ENTRY_SIZE
        btn_bytes = cfg.to_bytes()
        data[offset:offset + BUTTON_ENTRY_SIZE] = btn_bytes
    return list(data)


def read_buttons_from_device(dev):
    """Read current button configuration from the mouse."""
    send_startup(dev)
    section = read_section(dev, BUTTONS_ADDR)
    if section is None:
        return {}
    return parse_buttons_from_section(section)


def write_buttons_to_device(dev, buttons):
    """Write button configuration to the mouse."""
    send_startup(dev)
    section = build_button_section(buttons)
    write_section(dev, BUTTONS_ADDR, section)


# ─── GUI Application ────────────────────────────────────────────────────────

class ButtonAssignmentDialog(tk.Toplevel):
    """Dialog for assigning a key/action to a mouse button."""

    def __init__(self, parent, button_idx, current_config):
        super().__init__(parent)
        self.title(f"Assign - {BUTTON_NAMES.get(button_idx, f'Button {button_idx}')}")
        self.geometry("500x480")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result = None
        self.button_idx = button_idx

        # Action type selection
        type_frame = ttk.LabelFrame(self, text="Action Type", padding=10)
        type_frame.pack(fill="x", padx=10, pady=5)

        self.action_var = tk.StringVar(value="keyboard")
        actions = [
            ("Keyboard Key", "keyboard"),
            ("Keyboard Combo (Modifier + Key)", "combo"),
            ("Mouse Button", "mouse"),
            ("DPI Control", "dpi"),
            ("Multimedia", "media"),
            ("Disabled", "disabled"),
        ]
        for text, val in actions:
            ttk.Radiobutton(type_frame, text=text, variable=self.action_var,
                            value=val, command=self._update_options).pack(anchor="w")

        # Options frame (changes based on action type)
        self.options_frame = ttk.LabelFrame(self, text="Options", padding=10)
        self.options_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Key selection (for keyboard mode)
        self._build_keyboard_options()

        # Buttons
        btn_frame = ttk.Frame(self, padding=5)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="OK", command=self._ok).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right")

        # Set current config
        self._set_from_config(current_config)

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window()

    def _clear_options(self):
        for widget in self.options_frame.winfo_children():
            widget.destroy()

    def _build_keyboard_options(self):
        self._clear_options()

        # Modifiers
        mod_frame = ttk.Frame(self.options_frame)
        mod_frame.pack(fill="x", pady=2)
        ttk.Label(mod_frame, text="Modifiers:").pack(side="left")

        self.mod_lctrl = tk.BooleanVar()
        self.mod_lshift = tk.BooleanVar()
        self.mod_lalt = tk.BooleanVar()
        self.mod_lwin = tk.BooleanVar()

        ttk.Checkbutton(mod_frame, text="Ctrl", variable=self.mod_lctrl).pack(side="left", padx=3)
        ttk.Checkbutton(mod_frame, text="Shift", variable=self.mod_lshift).pack(side="left", padx=3)
        ttk.Checkbutton(mod_frame, text="Alt", variable=self.mod_lalt).pack(side="left", padx=3)
        ttk.Checkbutton(mod_frame, text="Win", variable=self.mod_lwin).pack(side="left", padx=3)

        # Key selection
        key_frame = ttk.Frame(self.options_frame)
        key_frame.pack(fill="x", pady=5)
        ttk.Label(key_frame, text="Key:").pack(side="left")

        self.key_var = tk.StringVar()
        all_keys = get_all_assignable_keys()
        key_names = [name for name, _ in all_keys]

        self.key_combo = ttk.Combobox(key_frame, textvariable=self.key_var,
                                       values=key_names, state="readonly", width=20)
        self.key_combo.pack(side="left", padx=5)

        # Quick F-key buttons
        fkey_frame = ttk.LabelFrame(self.options_frame, text="Quick Select: Function Keys",
                                     padding=5)
        fkey_frame.pack(fill="x", pady=5)

        # F1-F12 row
        row1 = ttk.Frame(fkey_frame)
        row1.pack(fill="x")
        for n in range(1, 13):
            btn = ttk.Button(row1, text=f"F{n}", width=4,
                             command=lambda n=n: self.key_var.set(f"F{n}"))
            btn.pack(side="left", padx=1, pady=1)

        # F13-F24 row (highlighted - these are the new keys!)
        row2 = ttk.Frame(fkey_frame)
        row2.pack(fill="x")
        for n in range(13, 25):
            btn = tk.Button(row2, text=f"F{n}", width=4, bg="#4CAF50", fg="white",
                            activebackground="#66BB6A", font=("", 8, "bold"),
                            command=lambda n=n: self.key_var.set(f"F{n}"))
            btn.pack(side="left", padx=1, pady=1)

        ttk.Label(fkey_frame, text="(Green = F13-F24, newly supported!)",
                  foreground="green").pack(anchor="w")

    def _build_combo_options(self):
        self._clear_options()

        ttk.Label(self.options_frame,
                  text="Select modifier(s) + key to send simultaneously.",
                  wraplength=400).pack(pady=(0, 5))

        # Modifiers
        mod_frame = ttk.Frame(self.options_frame)
        mod_frame.pack(fill="x", pady=2)
        ttk.Label(mod_frame, text="Modifiers:").pack(side="left")

        self.mod_lctrl = tk.BooleanVar(value=True)
        self.mod_lshift = tk.BooleanVar()
        self.mod_lalt = tk.BooleanVar()
        self.mod_lwin = tk.BooleanVar()

        ttk.Checkbutton(mod_frame, text="Ctrl", variable=self.mod_lctrl).pack(side="left", padx=3)
        ttk.Checkbutton(mod_frame, text="Shift", variable=self.mod_lshift).pack(side="left", padx=3)
        ttk.Checkbutton(mod_frame, text="Alt", variable=self.mod_lalt).pack(side="left", padx=3)
        ttk.Checkbutton(mod_frame, text="Win", variable=self.mod_lwin).pack(side="left", padx=3)

        # Key selection
        key_frame = ttk.Frame(self.options_frame)
        key_frame.pack(fill="x", pady=5)
        ttk.Label(key_frame, text="Key:").pack(side="left")

        self.key_var = tk.StringVar()
        all_keys = get_all_assignable_keys()
        key_names = [name for name, _ in all_keys]

        self.key_combo = ttk.Combobox(key_frame, textvariable=self.key_var,
                                       values=key_names, state="readonly", width=20)
        self.key_combo.pack(side="left", padx=5)

        # Quick F-key buttons
        fkey_frame = ttk.LabelFrame(self.options_frame, text="Quick Select", padding=5)
        fkey_frame.pack(fill="x", pady=5)
        row = ttk.Frame(fkey_frame)
        row.pack(fill="x")
        for n in range(13, 25):
            btn = tk.Button(row, text=f"F{n}", width=4, bg="#4CAF50", fg="white",
                            activebackground="#66BB6A", font=("", 8, "bold"),
                            command=lambda n=n: self.key_var.set(f"F{n}"))
            btn.pack(side="left", padx=1, pady=1)

    def _build_mouse_options(self):
        self._clear_options()
        self.mouse_var = tk.StringVar(value="Left Click")
        options = ["Left Click", "Right Click", "Middle Click", "Back", "Forward",
                   "Scroll Up", "Scroll Down"]
        for opt in options:
            ttk.Radiobutton(self.options_frame, text=opt, variable=self.mouse_var,
                            value=opt).pack(anchor="w")

    def _build_dpi_options(self):
        self._clear_options()
        self.dpi_var = tk.StringVar(value="DPI+")
        options = ["DPI+", "DPI-", "DPI Loop"]
        for opt in options:
            ttk.Radiobutton(self.options_frame, text=opt, variable=self.dpi_var,
                            value=opt).pack(anchor="w")

    def _build_media_options(self):
        self._clear_options()
        self.media_var = tk.StringVar(value="Play/Pause")
        options = ["Play/Pause", "Stop", "Next Track", "Previous Track",
                   "Volume Up", "Volume Down", "Mute"]
        for opt in options:
            ttk.Radiobutton(self.options_frame, text=opt, variable=self.media_var,
                            value=opt).pack(anchor="w")

    def _build_empty_options(self):
        self._clear_options()
        ttk.Label(self.options_frame, text="This button will be disabled.").pack()

    def _update_options(self):
        action = self.action_var.get()
        if action == "keyboard":
            self._build_keyboard_options()
        elif action == "combo":
            self._build_combo_options()
        elif action == "mouse":
            self._build_mouse_options()
        elif action == "dpi":
            self._build_dpi_options()
        elif action == "media":
            self._build_media_options()
        else:
            self._build_empty_options()

    def _set_from_config(self, cfg):
        """Populate dialog from existing ButtonConfig."""
        if cfg.is_disabled():
            self.action_var.set("disabled")
            self._update_options()
        elif cfg.btn_type == BTN_TYPE_KEYBOARD:
            # Show as combo if modifiers are set, plain keyboard otherwise
            if cfg.modifier:
                self.action_var.set("combo")
            else:
                self.action_var.set("keyboard")
            self._update_options()
            self.mod_lctrl.set(bool(cfg.modifier & HID_MOD_LCTRL))
            self.mod_lshift.set(bool(cfg.modifier & HID_MOD_LSHIFT))
            self.mod_lalt.set(bool(cfg.modifier & HID_MOD_LALT))
            self.mod_lwin.set(bool(cfg.modifier & HID_MOD_LGUI))
            key_name = HID_KEY_NAMES.get(cfg.key_code, "")
            if key_name:
                self.key_var.set(key_name)
        elif cfg.btn_type == BTN_TYPE_MOUSE:
            self.action_var.set("mouse")
            self._update_options()
            mouse_map = {
                MOUSE_LEFT_CLICK: "Left Click", MOUSE_RIGHT_CLICK: "Right Click",
                MOUSE_MIDDLE_CLICK: "Middle Click", MOUSE_BACK: "Back",
                MOUSE_FORWARD: "Forward", MOUSE_SCROLL_UP: "Scroll Up",
                MOUSE_SCROLL_DOWN: "Scroll Down",
            }
            self.mouse_var.set(mouse_map.get(cfg.key_code, "Left Click"))
        elif cfg.btn_type == BTN_TYPE_DPI:
            self.action_var.set("dpi")
            self._update_options()
            dpi_map = {DPI_PLUS: "DPI+", DPI_MINUS: "DPI-", DPI_LOOP: "DPI Loop"}
            self.dpi_var.set(dpi_map.get(cfg.key_code, "DPI+"))
        elif cfg.btn_type == BTN_TYPE_MULTIMEDIA:
            self.action_var.set("media")
            self._update_options()
        else:
            self.action_var.set("disabled")
            self._update_options()

    def _get_modifier(self):
        mod = 0
        if self.mod_lctrl.get():  mod |= HID_MOD_LCTRL
        if self.mod_lshift.get(): mod |= HID_MOD_LSHIFT
        if self.mod_lalt.get():   mod |= HID_MOD_LALT
        if self.mod_lwin.get():   mod |= HID_MOD_LGUI
        return mod

    def _ok(self):
        action = self.action_var.get()

        if action in ("keyboard", "combo"):
            key_name = self.key_var.get()
            if not key_name:
                messagebox.showwarning("No Key", "Please select a key.", parent=self)
                return
            hid_code = HID_NAME_TO_CODE.get(key_name, 0)
            modifier = self._get_modifier()
            self.result = ButtonConfig.keyboard_key(hid_code, modifier)

        elif action == "mouse":
            mouse_map = {
                "Left Click": MOUSE_LEFT_CLICK, "Right Click": MOUSE_RIGHT_CLICK,
                "Middle Click": MOUSE_MIDDLE_CLICK, "Back": MOUSE_BACK,
                "Forward": MOUSE_FORWARD, "Scroll Up": MOUSE_SCROLL_UP,
                "Scroll Down": MOUSE_SCROLL_DOWN,
            }
            code = mouse_map.get(self.mouse_var.get(), MOUSE_LEFT_CLICK)
            self.result = ButtonConfig.mouse_button(code)

        elif action == "dpi":
            dpi_map = {"DPI+": DPI_PLUS, "DPI-": DPI_MINUS, "DPI Loop": DPI_LOOP}
            code = dpi_map.get(self.dpi_var.get(), DPI_PLUS)
            self.result = ButtonConfig.dpi(code)

        elif action == "media":
            media_map = {
                "Play/Pause": MEDIA_PLAY_PAUSE, "Stop": MEDIA_STOP,
                "Next Track": MEDIA_NEXT, "Previous Track": MEDIA_PREV,
                "Volume Up": MEDIA_VOLUME_UP, "Volume Down": MEDIA_VOLUME_DOWN,
                "Mute": MEDIA_MUTE,
            }
            code = media_map.get(self.media_var.get(), MEDIA_PLAY_PAUSE)
            self.result = ButtonConfig.multimedia(code)

        elif action == "disabled":
            self.result = ButtonConfig.disabled()

        self.destroy()


class MX3100App(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title("MX-3100 Gaming Mouse Configurator (F13-F24 Support)")
        self.geometry("800x700")
        self.minsize(700, 600)

        # Current button configuration
        self.buttons = dict(DEFAULT_BUTTONS)
        self.device_connected = False
        self.current_profile = 0

        self._build_ui()
        self._refresh_button_list()

    def _build_ui(self):
        # Menu bar
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Load Profile...", command=self._load_profile)
        file_menu.add_command(label="Save Profile...", command=self._save_profile)
        file_menu.add_separator()
        file_menu.add_command(label="Reset to Defaults", command=self._reset_defaults)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        device_menu = tk.Menu(menubar, tearoff=0)
        device_menu.add_command(label="Detect Mouse", command=self._detect_device)
        device_menu.add_command(label="Read from Mouse", command=self._read_from_device)
        device_menu.add_command(label="Write to Mouse", command=self._write_to_device)
        menubar.add_cascade(label="Device", menu=device_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Quick Assign F13-F24...",
                               command=self._quick_assign_fkeys)
        tools_menu.add_command(label="HID Sniffer...", command=self._open_sniffer)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        # Status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", side="bottom", padx=5, pady=2)
        self.status_var = tk.StringVar(value="Ready - Click 'Detect Mouse' to connect")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side="left")

        # Main content
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Header
        header = ttk.Frame(main_frame)
        header.pack(fill="x", pady=(0, 10))

        ttk.Label(header, text="MX-3100 Gaming Mouse Configuration",
                  font=("", 14, "bold")).pack(side="left")

        # Profile selector
        prof_frame = ttk.Frame(header)
        prof_frame.pack(side="right")
        ttk.Label(prof_frame, text="Profile:").pack(side="left")
        self.profile_var = tk.StringVar(value="Profile 1")
        profile_combo = ttk.Combobox(prof_frame, textvariable=self.profile_var,
                                      values=[f"Profile {i+1}" for i in range(6)],
                                      state="readonly", width=12)
        profile_combo.pack(side="left", padx=5)

        # Button assignment table
        table_frame = ttk.LabelFrame(main_frame, text="Button Assignments", padding=10)
        table_frame.pack(fill="both", expand=True)

        # Treeview
        columns = ("button", "assignment")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                  height=20)
        self.tree.heading("button", text="Button")
        self.tree.heading("assignment", text="Current Assignment")
        self.tree.column("button", width=250)
        self.tree.column("assignment", width=400)
        self.tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical",
                                   command=self.tree.yview)
        scrollbar.pack(fill="y", side="right")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<Double-1>", self._on_double_click)

        # Action buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill="x", pady=10)

        ttk.Button(action_frame, text="Assign Key...",
                   command=self._assign_selected).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Quick F13-F24",
                   command=self._quick_assign_fkeys).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Set Disabled",
                   command=self._disable_selected).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Reset to Default",
                   command=self._reset_selected).pack(side="left", padx=5)

        sep = ttk.Separator(action_frame, orient="vertical")
        sep.pack(side="left", fill="y", padx=10)

        ttk.Button(action_frame, text="Write to Mouse",
                   command=self._write_to_device).pack(side="right", padx=5)
        ttk.Button(action_frame, text="Read from Mouse",
                   command=self._read_from_device).pack(side="right", padx=5)

    def _refresh_button_list(self):
        """Update the treeview with current button assignments."""
        self.tree.delete(*self.tree.get_children())
        for btn_idx in range(TOTAL_BUTTONS):
            name = BUTTON_NAMES.get(btn_idx, f"Button {btn_idx}")
            cfg = self.buttons.get(btn_idx, ButtonConfig.default())
            desc = cfg.describe()
            self.tree.insert("", "end", iid=str(btn_idx),
                             values=(name, desc))

    def _get_selected_button(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select Button", "Please select a button first.")
            return None
        return int(sel[0])

    def _on_double_click(self, event):
        self._assign_selected()

    def _assign_selected(self):
        btn_idx = self._get_selected_button()
        if btn_idx is None:
            return
        current = self.buttons.get(btn_idx, ButtonConfig.default())
        dialog = ButtonAssignmentDialog(self, btn_idx, current)
        if dialog.result is not None:
            self.buttons[btn_idx] = dialog.result
            self._refresh_button_list()
            self.status_var.set(
                f"Assigned {dialog.result.describe()} to "
                f"{BUTTON_NAMES.get(btn_idx, f'Button {btn_idx}')}"
            )

    def _disable_selected(self):
        btn_idx = self._get_selected_button()
        if btn_idx is None:
            return
        self.buttons[btn_idx] = ButtonConfig.disabled()
        self._refresh_button_list()

    def _reset_selected(self):
        btn_idx = self._get_selected_button()
        if btn_idx is None:
            return
        self.buttons[btn_idx] = DEFAULT_BUTTONS.get(btn_idx, ButtonConfig.default())
        self._refresh_button_list()

    def _reset_defaults(self):
        if messagebox.askyesno("Reset", "Reset all buttons to defaults?"):
            self.buttons = dict(DEFAULT_BUTTONS)
            self._refresh_button_list()
            self.status_var.set("All buttons reset to defaults")

    def _quick_assign_fkeys(self):
        """Dialog to quickly assign F13-F24 to side buttons."""
        dlg = tk.Toplevel(self)
        dlg.title("Quick Assign F13-F24 to Side Buttons")
        dlg.geometry("450x550")
        dlg.transient(self)
        dlg.grab_set()

        ttk.Label(dlg, text="Map F13-F24 to side buttons:",
                  font=("", 11, "bold")).pack(pady=5)
        ttk.Label(dlg, text="Select which F-key each side button should send.",
                  wraplength=400).pack(pady=2)

        assignments = {}
        frame = ttk.Frame(dlg, padding=10)
        frame.pack(fill="both", expand=True)

        fkey_options = ["(unchanged)"] + [f"F{n}" for n in range(13, 25)]

        for i, btn_idx in enumerate(range(7, TOTAL_BUTTONS)):
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=2)
            name = BUTTON_NAMES.get(btn_idx, f"Button {btn_idx}")
            ttk.Label(row, text=name, width=20).pack(side="left")
            ttk.Label(row, text="→", width=3).pack(side="left")

            var = tk.StringVar(value=fkey_options[min(i + 1, len(fkey_options) - 1)])
            combo = ttk.Combobox(row, textvariable=var, values=fkey_options,
                                  state="readonly", width=15)
            combo.pack(side="left", padx=5)
            assignments[btn_idx] = var

        def apply():
            for btn_idx, var in assignments.items():
                val = var.get()
                if val != "(unchanged)" and val.startswith("F"):
                    n = int(val[1:])
                    self.buttons[btn_idx] = ButtonConfig.f_key(n)
            self._refresh_button_list()
            self.status_var.set("F13-F24 keys assigned to side buttons")
            dlg.destroy()

        btn_frame = ttk.Frame(dlg, padding=5)
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Apply", command=apply).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dlg.destroy).pack(side="right")

    def _detect_device(self):
        """Detect if the mouse is connected."""
        self.status_var.set("Searching for MX-3100 mouse...")
        self.update()

        devices = enumerate_devices()
        if devices:
            self.device_connected = True
            info = "\n".join(
                f"  Interface: UsagePage=0x{d[1]:04X}, Usage=0x{d[2]:04X}, "
                f"FeatureLen={d[3]}"
                for d in devices
            )
            self.status_var.set(f"Mouse detected! ({len(devices)} HID interface(s))")
            messagebox.showinfo("Device Found",
                                f"MX-3100 mouse detected!\n\n"
                                f"Found {len(devices)} HID interface(s):\n{info}")
        else:
            self.device_connected = False
            self.status_var.set("Mouse not found")
            messagebox.showwarning(
                "Not Found",
                "MX-3100 mouse not detected.\n\n"
                "Make sure:\n"
                "1. The mouse is plugged in via USB\n"
                "2. You're running as Administrator\n"
                "3. No other mouse software is running"
            )

    def _read_from_device(self):
        """Read current button config from the mouse."""
        try:
            self.status_var.set("Reading configuration from mouse...")
            self.update()
            with MX3100Device() as dev:
                buttons = read_buttons_from_device(dev)
                if buttons:
                    self.buttons.update(buttons)
                    self._refresh_button_list()
                    self.status_var.set("Configuration read from mouse")
                else:
                    self.status_var.set("Read completed but no button data received")
                    messagebox.showwarning(
                        "Read Failed",
                        "Could not read button data from mouse.\n\n"
                        "Make sure you're running as Administrator."
                    )
        except IOError as e:
            self.status_var.set(f"Read failed: {e}")
            messagebox.showerror("Read Error",
                                 f"Failed to read from mouse:\n{e}\n\n"
                                 "Make sure you're running as Administrator.")

    def _write_to_device(self):
        """Write current button config to the mouse."""
        if not messagebox.askyesno("Confirm Write",
                                    "Write the current button assignments to the mouse?\n\n"
                                    "This will overwrite the current mouse configuration."):
            return
        try:
            self.status_var.set("Writing configuration to mouse...")
            self.update()
            with MX3100Device() as dev:
                write_buttons_to_device(dev, self.buttons)
                self.status_var.set("Configuration written to mouse successfully!")
                messagebox.showinfo("Success",
                                    "Button assignments written to mouse!\n\n"
                                    "The changes should take effect immediately.")
        except IOError as e:
            self.status_var.set(f"Write failed: {e}")
            messagebox.showerror("Write Error",
                                 f"Failed to write to mouse:\n{e}\n\n"
                                 "Make sure you're running as Administrator "
                                 "and no other mouse software is running.")

    def _save_profile(self):
        """Save current config to a JSON file."""
        filename = filedialog.asksaveasfilename(
            title="Save Profile",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=PROFILE_DIR,
        )
        if filename:
            save_profile(filename, self.buttons)
            self.status_var.set(f"Profile saved to {os.path.basename(filename)}")

    def _load_profile(self):
        """Load config from a JSON file."""
        filename = filedialog.askopenfilename(
            title="Load Profile",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=PROFILE_DIR,
        )
        if filename:
            try:
                self.buttons = load_profile(filename)
                self._refresh_button_list()
                self.status_var.set(f"Profile loaded from {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Load Error", f"Failed to load profile:\n{e}")

    def _open_sniffer(self):
        """Open sniffer in a terminal."""
        import subprocess
        subprocess.Popen(
            [sys.executable, "mx3100_sniffer.py", "--probe"],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        self.status_var.set("HID Sniffer launched in new window")


# ─── CLI Mode ────────────────────────────────────────────────────────────────

def cli_detect():
    print("Searching for MX-3100 mouse (VID:04D9, PID:A11B)...")
    devices = enumerate_devices()
    if not devices:
        print("ERROR: Mouse not found.")
        return False

    print(f"Found {len(devices)} HID interface(s):")
    for i, (path, up, u, fl, il, ol) in enumerate(devices):
        print(f"  [{i}] UsagePage=0x{up:04X} Usage=0x{u:04X} "
              f"Feature={fl}B Input={il}B Output={ol}B")
    return True


def cli_assign(button_idx, key_name, modifier_str=""):
    """Assign a key to a button via CLI."""
    if key_name not in HID_NAME_TO_CODE:
        print(f"ERROR: Unknown key '{key_name}'")
        print(f"Valid keys: {', '.join(sorted(HID_NAME_TO_CODE.keys()))}")
        return

    hid_code = HID_NAME_TO_CODE[key_name]
    modifier = 0
    if modifier_str:
        for mod in modifier_str.split("+"):
            mod = mod.strip().lower()
            if mod in ("ctrl", "lctrl"):    modifier |= HID_MOD_LCTRL
            elif mod in ("shift", "lshift"): modifier |= HID_MOD_LSHIFT
            elif mod in ("alt", "lalt"):     modifier |= HID_MOD_LALT
            elif mod in ("win", "lwin"):     modifier |= HID_MOD_LGUI

    cfg = ButtonConfig.keyboard_key(hid_code, modifier)
    print(f"Assigning {cfg.describe()} to button {button_idx}...")

    try:
        with MX3100Device() as dev:
            # Read current config first
            print("Reading current config...")
            buttons = read_buttons_from_device(dev)
            if not buttons:
                buttons = dict(DEFAULT_BUTTONS)
            buttons[button_idx] = cfg
            print("Writing updated config...")
            write_buttons_to_device(dev, buttons)
            print("Done!")
    except IOError as e:
        print(f"ERROR: {e}")


def cli_list_keys():
    print("Available keys (including F13-F24):\n")
    keys = get_all_assignable_keys()
    for name, code in keys:
        marker = " *NEW*" if name.startswith("F") and name[1:].isdigit() and int(name[1:]) >= 13 else ""
        print(f"  {name:<15} (HID 0x{code:02X}){marker}")
    print("\n*NEW* = F13-F24 (newly supported)")


def cli_read():
    """Read and display current button assignments from mouse."""
    print("Reading button assignments from mouse...")
    try:
        with MX3100Device() as dev:
            buttons = read_buttons_from_device(dev)
            if not buttons:
                print("ERROR: Could not read button data.")
                return
            print(f"\nCurrent button assignments ({len(buttons)} buttons):\n")
            for btn_idx in range(TOTAL_BUTTONS):
                name = BUTTON_NAMES.get(btn_idx, f"Button {btn_idx}")
                cfg = buttons.get(btn_idx, ButtonConfig.disabled())
                raw = cfg.to_bytes()
                hex_str = " ".join(f"{b:02X}" for b in raw)
                print(f"  [{btn_idx:2d}] {name:<30} {cfg.describe():<25} [{hex_str}]")
    except IOError as e:
        print(f"ERROR: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="MX-3100 Gaming Mouse Configurator with F13-F24 Support"
    )
    parser.add_argument("--cli", action="store_true",
                        help="Use command-line mode (no GUI)")
    parser.add_argument("--detect", action="store_true",
                        help="Just detect the mouse and exit")
    parser.add_argument("--read", action="store_true",
                        help="Read and display current button assignments")
    parser.add_argument("--assign", nargs=2, metavar=("BUTTON", "KEY"),
                        help="Assign a key to a button (e.g. --assign 7 F13)")
    parser.add_argument("--modifier", type=str, default="",
                        help="Modifier keys (e.g. 'ctrl+shift')")
    parser.add_argument("--list-keys", action="store_true",
                        help="List all assignable keys")
    parser.add_argument("--save-profile", type=str, metavar="FILE",
                        help="Save current config to JSON file")
    parser.add_argument("--load-profile", type=str, metavar="FILE",
                        help="Load and apply config from JSON file")

    args = parser.parse_args()

    if args.detect:
        cli_detect()
    elif args.list_keys:
        cli_list_keys()
    elif args.read:
        cli_read()
    elif args.assign:
        btn_idx = int(args.assign[0])
        key_name = args.assign[1]
        cli_assign(btn_idx, key_name, args.modifier)
    elif args.cli:
        print("MX-3100 Mouse Configurator - CLI Mode")
        print("Use --help for available commands")
        cli_detect()
    else:
        app = MX3100App()
        app.mainloop()


if __name__ == "__main__":
    main()
