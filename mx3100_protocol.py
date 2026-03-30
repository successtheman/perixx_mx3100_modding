"""
Perixx MX-3100 Gaming Mouse - Protocol Constants & Key Mappings

Contains USB HID usage codes, button definitions, and the protocol
structure for communicating with the Holtek-based mouse firmware.
"""

# ─── USB HID Keyboard Usage Codes (Usage Page 0x07) ─────────────────────────
# Reference: USB HID Usage Tables v1.4, Section 10 (Keyboard/Keypad Page)

HID_KEY_NONE = 0x00
HID_KEY_A = 0x04
HID_KEY_B = 0x05
HID_KEY_C = 0x06
HID_KEY_D = 0x07
HID_KEY_E = 0x08
HID_KEY_F = 0x09
HID_KEY_G = 0x0A
HID_KEY_H = 0x0B
HID_KEY_I = 0x0C
HID_KEY_J = 0x0D
HID_KEY_K = 0x0E
HID_KEY_L = 0x0F
HID_KEY_M = 0x10
HID_KEY_N = 0x11
HID_KEY_O = 0x12
HID_KEY_P = 0x13
HID_KEY_Q = 0x14
HID_KEY_R = 0x15
HID_KEY_S = 0x16
HID_KEY_T = 0x17
HID_KEY_U = 0x18
HID_KEY_V = 0x19
HID_KEY_W = 0x1A
HID_KEY_X = 0x1B
HID_KEY_Y = 0x1C
HID_KEY_Z = 0x1D
HID_KEY_1 = 0x1E
HID_KEY_2 = 0x1F
HID_KEY_3 = 0x20
HID_KEY_4 = 0x21
HID_KEY_5 = 0x22
HID_KEY_6 = 0x23
HID_KEY_7 = 0x24
HID_KEY_8 = 0x25
HID_KEY_9 = 0x26
HID_KEY_0 = 0x27
HID_KEY_ENTER = 0x28
HID_KEY_ESCAPE = 0x29
HID_KEY_BACKSPACE = 0x2A
HID_KEY_TAB = 0x2B
HID_KEY_SPACE = 0x2C
HID_KEY_MINUS = 0x2D
HID_KEY_EQUAL = 0x2E
HID_KEY_LBRACKET = 0x2F
HID_KEY_RBRACKET = 0x30
HID_KEY_BACKSLASH = 0x31
HID_KEY_SEMICOLON = 0x33
HID_KEY_APOSTROPHE = 0x34
HID_KEY_GRAVE = 0x35
HID_KEY_COMMA = 0x36
HID_KEY_DOT = 0x37
HID_KEY_SLASH = 0x38
HID_KEY_CAPSLOCK = 0x39
HID_KEY_F1 = 0x3A
HID_KEY_F2 = 0x3B
HID_KEY_F3 = 0x3C
HID_KEY_F4 = 0x3D
HID_KEY_F5 = 0x3E
HID_KEY_F6 = 0x3F
HID_KEY_F7 = 0x40
HID_KEY_F8 = 0x41
HID_KEY_F9 = 0x42
HID_KEY_F10 = 0x43
HID_KEY_F11 = 0x44
HID_KEY_F12 = 0x45
HID_KEY_PRINTSCREEN = 0x46
HID_KEY_SCROLLLOCK = 0x47
HID_KEY_PAUSE = 0x48
HID_KEY_INSERT = 0x49
HID_KEY_HOME = 0x4A
HID_KEY_PAGEUP = 0x4B
HID_KEY_DELETE = 0x4C
HID_KEY_END = 0x4D
HID_KEY_PAGEDOWN = 0x4E
HID_KEY_RIGHT = 0x4F
HID_KEY_LEFT = 0x50
HID_KEY_DOWN = 0x51
HID_KEY_UP = 0x52
HID_KEY_NUMLOCK = 0x53
HID_KEY_KP_SLASH = 0x54
HID_KEY_KP_ASTERISK = 0x55
HID_KEY_KP_MINUS = 0x56
HID_KEY_KP_PLUS = 0x57
HID_KEY_KP_ENTER = 0x58
HID_KEY_KP_1 = 0x59
HID_KEY_KP_2 = 0x5A
HID_KEY_KP_3 = 0x5B
HID_KEY_KP_4 = 0x5C
HID_KEY_KP_5 = 0x5D
HID_KEY_KP_6 = 0x5E
HID_KEY_KP_7 = 0x5F
HID_KEY_KP_8 = 0x60
HID_KEY_KP_9 = 0x61
HID_KEY_KP_0 = 0x62
HID_KEY_KP_DOT = 0x63

# ─── F13-F24 (the keys the user wants!) ─────────────────────────────────────
HID_KEY_F13 = 0x68
HID_KEY_F14 = 0x69
HID_KEY_F15 = 0x6A
HID_KEY_F16 = 0x6B
HID_KEY_F17 = 0x6C
HID_KEY_F18 = 0x6D
HID_KEY_F19 = 0x6E
HID_KEY_F20 = 0x6F
HID_KEY_F21 = 0x70
HID_KEY_F22 = 0x71
HID_KEY_F23 = 0x72
HID_KEY_F24 = 0x73

# ─── HID Modifier bit flags (byte in keyboard report) ───────────────────────
HID_MOD_NONE = 0x00
HID_MOD_LCTRL = 0x01
HID_MOD_LSHIFT = 0x02
HID_MOD_LALT = 0x04
HID_MOD_LGUI = 0x08
HID_MOD_RCTRL = 0x10
HID_MOD_RSHIFT = 0x20
HID_MOD_RALT = 0x40
HID_MOD_RGUI = 0x80

# ─── Windows Virtual Key to HID Usage Code mapping ──────────────────────────
# (VK codes the original driver captures via keyboard hook)
VK_TO_HID = {
    0x08: HID_KEY_BACKSPACE,  # VK_BACK
    0x09: HID_KEY_TAB,        # VK_TAB
    0x0D: HID_KEY_ENTER,      # VK_RETURN
    0x1B: HID_KEY_ESCAPE,     # VK_ESCAPE
    0x20: HID_KEY_SPACE,      # VK_SPACE
    0x21: HID_KEY_PAGEUP,     # VK_PRIOR
    0x22: HID_KEY_PAGEDOWN,   # VK_NEXT
    0x23: HID_KEY_END,        # VK_END
    0x24: HID_KEY_HOME,       # VK_HOME
    0x25: HID_KEY_LEFT,       # VK_LEFT
    0x26: HID_KEY_UP,         # VK_UP
    0x27: HID_KEY_RIGHT,      # VK_RIGHT
    0x28: HID_KEY_DOWN,       # VK_DOWN
    0x2C: HID_KEY_PRINTSCREEN,  # VK_SNAPSHOT
    0x2D: HID_KEY_INSERT,     # VK_INSERT
    0x2E: HID_KEY_DELETE,     # VK_DELETE
    0x30: HID_KEY_0, 0x31: HID_KEY_1, 0x32: HID_KEY_2, 0x33: HID_KEY_3,
    0x34: HID_KEY_4, 0x35: HID_KEY_5, 0x36: HID_KEY_6, 0x37: HID_KEY_7,
    0x38: HID_KEY_8, 0x39: HID_KEY_9,
    0x41: HID_KEY_A, 0x42: HID_KEY_B, 0x43: HID_KEY_C, 0x44: HID_KEY_D,
    0x45: HID_KEY_E, 0x46: HID_KEY_F, 0x47: HID_KEY_G, 0x48: HID_KEY_H,
    0x49: HID_KEY_I, 0x4A: HID_KEY_J, 0x4B: HID_KEY_K, 0x4C: HID_KEY_L,
    0x4D: HID_KEY_M, 0x4E: HID_KEY_N, 0x4F: HID_KEY_O, 0x50: HID_KEY_P,
    0x51: HID_KEY_Q, 0x52: HID_KEY_R, 0x53: HID_KEY_S, 0x54: HID_KEY_T,
    0x55: HID_KEY_U, 0x56: HID_KEY_V, 0x57: HID_KEY_W, 0x58: HID_KEY_X,
    0x59: HID_KEY_Y, 0x5A: HID_KEY_Z,
    0x60: HID_KEY_KP_0, 0x61: HID_KEY_KP_1, 0x62: HID_KEY_KP_2,
    0x63: HID_KEY_KP_3, 0x64: HID_KEY_KP_4, 0x65: HID_KEY_KP_5,
    0x66: HID_KEY_KP_6, 0x67: HID_KEY_KP_7, 0x68: HID_KEY_KP_8,
    0x69: HID_KEY_KP_9, 0x6A: HID_KEY_KP_ASTERISK, 0x6B: HID_KEY_KP_PLUS,
    0x6D: HID_KEY_KP_MINUS, 0x6E: HID_KEY_KP_DOT, 0x6F: HID_KEY_KP_SLASH,
    0x70: HID_KEY_F1,  0x71: HID_KEY_F2,  0x72: HID_KEY_F3,  0x73: HID_KEY_F4,
    0x74: HID_KEY_F5,  0x75: HID_KEY_F6,  0x76: HID_KEY_F7,  0x77: HID_KEY_F8,
    0x78: HID_KEY_F9,  0x79: HID_KEY_F10, 0x7A: HID_KEY_F11, 0x7B: HID_KEY_F12,
    0x7C: HID_KEY_F13, 0x7D: HID_KEY_F14, 0x7E: HID_KEY_F15, 0x7F: HID_KEY_F16,
    0x80: HID_KEY_F17, 0x81: HID_KEY_F18, 0x82: HID_KEY_F19, 0x83: HID_KEY_F20,
    0x84: HID_KEY_F21, 0x85: HID_KEY_F22, 0x86: HID_KEY_F23, 0x87: HID_KEY_F24,
    0x90: HID_KEY_NUMLOCK,      # VK_NUMLOCK
    0x91: HID_KEY_SCROLLLOCK,   # VK_SCROLL
    0x14: HID_KEY_CAPSLOCK,     # VK_CAPITAL
    0xBA: HID_KEY_SEMICOLON,    # VK_OEM_1
    0xBB: HID_KEY_EQUAL,        # VK_OEM_PLUS
    0xBC: HID_KEY_COMMA,        # VK_OEM_COMMA
    0xBD: HID_KEY_MINUS,        # VK_OEM_MINUS
    0xBE: HID_KEY_DOT,          # VK_OEM_PERIOD
    0xBF: HID_KEY_SLASH,        # VK_OEM_2
    0xC0: HID_KEY_GRAVE,        # VK_OEM_3
    0xDB: HID_KEY_LBRACKET,     # VK_OEM_4
    0xDC: HID_KEY_BACKSLASH,    # VK_OEM_5
    0xDD: HID_KEY_RBRACKET,     # VK_OEM_6
    0xDE: HID_KEY_APOSTROPHE,   # VK_OEM_7
    0x13: HID_KEY_PAUSE,        # VK_PAUSE
}

# ─── Human-readable key name table ──────────────────────────────────────────

HID_KEY_NAMES = {
    HID_KEY_NONE: "(None)",
    HID_KEY_A: "A", HID_KEY_B: "B", HID_KEY_C: "C", HID_KEY_D: "D",
    HID_KEY_E: "E", HID_KEY_F: "F", HID_KEY_G: "G", HID_KEY_H: "H",
    HID_KEY_I: "I", HID_KEY_J: "J", HID_KEY_K: "K", HID_KEY_L: "L",
    HID_KEY_M: "M", HID_KEY_N: "N", HID_KEY_O: "O", HID_KEY_P: "P",
    HID_KEY_Q: "Q", HID_KEY_R: "R", HID_KEY_S: "S", HID_KEY_T: "T",
    HID_KEY_U: "U", HID_KEY_V: "V", HID_KEY_W: "W", HID_KEY_X: "X",
    HID_KEY_Y: "Y", HID_KEY_Z: "Z",
    HID_KEY_1: "1", HID_KEY_2: "2", HID_KEY_3: "3", HID_KEY_4: "4",
    HID_KEY_5: "5", HID_KEY_6: "6", HID_KEY_7: "7", HID_KEY_8: "8",
    HID_KEY_9: "9", HID_KEY_0: "0",
    HID_KEY_ENTER: "Enter", HID_KEY_ESCAPE: "Escape",
    HID_KEY_BACKSPACE: "Backspace", HID_KEY_TAB: "Tab",
    HID_KEY_SPACE: "Space", HID_KEY_MINUS: "-", HID_KEY_EQUAL: "=",
    HID_KEY_LBRACKET: "[", HID_KEY_RBRACKET: "]", HID_KEY_BACKSLASH: "\\",
    HID_KEY_SEMICOLON: ";", HID_KEY_APOSTROPHE: "'", HID_KEY_GRAVE: "`",
    HID_KEY_COMMA: ",", HID_KEY_DOT: ".", HID_KEY_SLASH: "/",
    HID_KEY_CAPSLOCK: "CapsLock",
    HID_KEY_F1: "F1", HID_KEY_F2: "F2", HID_KEY_F3: "F3", HID_KEY_F4: "F4",
    HID_KEY_F5: "F5", HID_KEY_F6: "F6", HID_KEY_F7: "F7", HID_KEY_F8: "F8",
    HID_KEY_F9: "F9", HID_KEY_F10: "F10", HID_KEY_F11: "F11", HID_KEY_F12: "F12",
    HID_KEY_F13: "F13", HID_KEY_F14: "F14", HID_KEY_F15: "F15", HID_KEY_F16: "F16",
    HID_KEY_F17: "F17", HID_KEY_F18: "F18", HID_KEY_F19: "F19", HID_KEY_F20: "F20",
    HID_KEY_F21: "F21", HID_KEY_F22: "F22", HID_KEY_F23: "F23", HID_KEY_F24: "F24",
    HID_KEY_PRINTSCREEN: "PrintScreen", HID_KEY_SCROLLLOCK: "ScrollLock",
    HID_KEY_PAUSE: "Pause", HID_KEY_INSERT: "Insert", HID_KEY_HOME: "Home",
    HID_KEY_PAGEUP: "PageUp", HID_KEY_DELETE: "Delete", HID_KEY_END: "End",
    HID_KEY_PAGEDOWN: "PageDown", HID_KEY_RIGHT: "Right", HID_KEY_LEFT: "Left",
    HID_KEY_DOWN: "Down", HID_KEY_UP: "Up", HID_KEY_NUMLOCK: "NumLock",
    HID_KEY_KP_SLASH: "KP /", HID_KEY_KP_ASTERISK: "KP *",
    HID_KEY_KP_MINUS: "KP -", HID_KEY_KP_PLUS: "KP +",
    HID_KEY_KP_ENTER: "KP Enter",
    HID_KEY_KP_1: "KP 1", HID_KEY_KP_2: "KP 2", HID_KEY_KP_3: "KP 3",
    HID_KEY_KP_4: "KP 4", HID_KEY_KP_5: "KP 5", HID_KEY_KP_6: "KP 6",
    HID_KEY_KP_7: "KP 7", HID_KEY_KP_8: "KP 8", HID_KEY_KP_9: "KP 9",
    HID_KEY_KP_0: "KP 0", HID_KEY_KP_DOT: "KP .",
}

# Reverse lookup: name -> HID code
HID_NAME_TO_CODE = {v: k for k, v in HID_KEY_NAMES.items() if k != HID_KEY_NONE}

# ─── Mouse button action types ──────────────────────────────────────────────
# These define what a button does when pressed

ACTION_DEFAULT = 0x00       # Default mouse button function
ACTION_KEYBOARD = 0x01      # Single keyboard key (with optional modifiers)
ACTION_MOUSE_BUTTON = 0x02  # Mouse button (left/right/middle click)
ACTION_MULTIMEDIA = 0x03    # Multimedia key (play, volume, etc.)
ACTION_DPI = 0x04           # DPI control (DPI+, DPI-, DPI loop, specific stage)
ACTION_MACRO = 0x05         # Macro playback
ACTION_DISABLED = 0x06      # Button disabled
ACTION_FIRE_KEY = 0x07      # Fire key (rapid repeat)
ACTION_COMBO_KEY = 0x08     # Combo key (multiple simultaneous keys)
ACTION_SNIPE_KEY = 0x09     # Snipe key (temporary DPI reduction)
ACTION_SCROLL = 0x0A        # Scroll functions
ACTION_PROFILE = 0x0B       # Profile switching
ACTION_REPORT_RATE = 0x0C   # Report rate switching

# ─── Mouse button default functions ─────────────────────────────────────────

MOUSE_LEFT_CLICK = 0x01
MOUSE_RIGHT_CLICK = 0x02
MOUSE_MIDDLE_CLICK = 0x04
MOUSE_BACK = 0x08
MOUSE_FORWARD = 0x10

# ─── DPI action sub-types ───────────────────────────────────────────────────

DPI_PLUS = 0x01
DPI_MINUS = 0x02
DPI_LOOP = 0x03
DPI_STAGE_1 = 0x11
DPI_STAGE_2 = 0x12
DPI_STAGE_3 = 0x13
DPI_STAGE_4 = 0x14
DPI_STAGE_5 = 0x15
DPI_STAGE_6 = 0x16
DPI_STAGE_7 = 0x17
DPI_STAGE_8 = 0x18

# ─── Scroll action sub-types ────────────────────────────────────────────────

SCROLL_UP = 0x01
SCROLL_DOWN = 0x02
SCROLL_LEFT = 0x03
SCROLL_RIGHT = 0x04
SCROLL_SCREEN = 0x05
SCROLL_UNIVERSAL = 0x06

# ─── Multimedia key codes (HID Consumer Usage Page 0x0C) ────────────────────

MEDIA_PLAY_PAUSE = 0xCD
MEDIA_STOP = 0xB7
MEDIA_NEXT = 0xB5
MEDIA_PREV = 0xB6
MEDIA_VOLUME_UP = 0xE9
MEDIA_VOLUME_DOWN = 0xEA
MEDIA_MUTE = 0xE2
MEDIA_BROWSER_HOME = 0x0223
MEDIA_BROWSER_BACK = 0x0224
MEDIA_BROWSER_FORWARD = 0x0225
MEDIA_MAIL = 0x018A
MEDIA_CALCULATOR = 0x0192
MEDIA_MY_COMPUTER = 0x0194

# ─── Button info ─────────────────────────────────────────────────────────────

BUTTON_NAMES = {
    0:  "Button 1 (Left Click)",
    1:  "Button 2 (Right Click)",
    2:  "Button 3 (Scroll Click)",
    3:  "Button 4 (Scroll Right Tilt)",
    4:  "Button 5 (Scroll Left Tilt)",
    5:  "Button 6 (DPI+)",
    6:  "Button 7 (DPI-)",
    7:  "Side Button S1",
    8:  "Side Button S2",
    9:  "Side Button S3",
    10: "Side Button S4",
    11: "Side Button S5",
    12: "Side Button S6",
    13: "Side Button S7",
    14: "Side Button S8",
    15: "Side Button S9",
    16: "Side Button S10",
    17: "Side Button S11",
    18: "Side Button S12",
}

TOTAL_BUTTONS = 19

# ─── Action type names ───────────────────────────────────────────────────────

ACTION_NAMES = {
    ACTION_DEFAULT: "Default",
    ACTION_KEYBOARD: "Keyboard Key",
    ACTION_MOUSE_BUTTON: "Mouse Button",
    ACTION_MULTIMEDIA: "Multimedia",
    ACTION_DPI: "DPI Control",
    ACTION_MACRO: "Macro",
    ACTION_DISABLED: "Disabled",
    ACTION_FIRE_KEY: "Fire Key",
    ACTION_COMBO_KEY: "Combo Key",
    ACTION_SNIPE_KEY: "Snipe Key",
    ACTION_SCROLL: "Scroll",
    ACTION_PROFILE: "Profile Switch",
    ACTION_REPORT_RATE: "Report Rate",
}


class ButtonConfig:
    """Represents a single button's configuration."""

    def __init__(self, action_type=ACTION_DEFAULT, modifier=0, key_code=0,
                 extra1=0, extra2=0):
        self.action_type = action_type
        self.modifier = modifier
        self.key_code = key_code
        self.extra1 = extra1
        self.extra2 = extra2

    def to_bytes(self):
        return bytes([self.action_type, self.modifier, self.key_code,
                      self.extra1, self.extra2])

    @classmethod
    def from_bytes(cls, data):
        if len(data) < 5:
            data = data + bytes(5 - len(data))
        return cls(data[0], data[1], data[2], data[3], data[4])

    def describe(self):
        """Human-readable description of button config."""
        if self.action_type == ACTION_DEFAULT:
            return "Default"
        elif self.action_type == ACTION_KEYBOARD:
            parts = []
            if self.modifier & HID_MOD_LCTRL:  parts.append("LCtrl")
            if self.modifier & HID_MOD_LSHIFT: parts.append("LShift")
            if self.modifier & HID_MOD_LALT:   parts.append("LAlt")
            if self.modifier & HID_MOD_LGUI:   parts.append("LWin")
            if self.modifier & HID_MOD_RCTRL:  parts.append("RCtrl")
            if self.modifier & HID_MOD_RSHIFT: parts.append("RShift")
            if self.modifier & HID_MOD_RALT:   parts.append("RAlt")
            if self.modifier & HID_MOD_RGUI:   parts.append("RWin")
            key_name = HID_KEY_NAMES.get(self.key_code, f"0x{self.key_code:02X}")
            parts.append(key_name)
            return " + ".join(parts)
        elif self.action_type == ACTION_DISABLED:
            return "Disabled"
        elif self.action_type == ACTION_DPI:
            dpi_names = {
                DPI_PLUS: "DPI+", DPI_MINUS: "DPI-", DPI_LOOP: "DPI Loop",
            }
            for i in range(1, 9):
                dpi_names[0x10 + i] = f"DPI Stage {i}"
            return dpi_names.get(self.key_code, f"DPI 0x{self.key_code:02X}")
        elif self.action_type == ACTION_MOUSE_BUTTON:
            names = {1: "Left Click", 2: "Right Click", 4: "Middle Click",
                     8: "Back", 16: "Forward"}
            return names.get(self.key_code, f"Mouse 0x{self.key_code:02X}")
        else:
            name = ACTION_NAMES.get(self.action_type, f"Type 0x{self.action_type:02X}")
            return f"{name} (0x{self.key_code:02X})"

    @classmethod
    def keyboard_key(cls, hid_code, modifier=0):
        """Create a keyboard key assignment."""
        return cls(ACTION_KEYBOARD, modifier, hid_code)

    @classmethod
    def f_key(cls, n, modifier=0):
        """Create an F-key assignment (F1-F24)."""
        if 1 <= n <= 12:
            code = 0x39 + n  # F1=0x3A, F12=0x45
        elif 13 <= n <= 24:
            code = 0x5B + n  # F13=0x68, F24=0x73
        else:
            raise ValueError(f"F{n} is not a valid function key (1-24)")
        return cls(ACTION_KEYBOARD, modifier, code)

    @classmethod
    def disabled(cls):
        return cls(ACTION_DISABLED)

    @classmethod
    def default(cls):
        return cls(ACTION_DEFAULT)


# ─── Default button assignments ──────────────────────────────────────────────

DEFAULT_BUTTONS = {
    0: ButtonConfig(ACTION_MOUSE_BUTTON, 0, MOUSE_LEFT_CLICK),   # Left click
    1: ButtonConfig(ACTION_MOUSE_BUTTON, 0, MOUSE_RIGHT_CLICK),  # Right click
    2: ButtonConfig(ACTION_SCROLL, 0, SCROLL_UNIVERSAL),          # Scroll click
    3: ButtonConfig(ACTION_SCROLL, 0, SCROLL_RIGHT),              # Scroll right tilt
    4: ButtonConfig(ACTION_SCROLL, 0, SCROLL_LEFT),               # Scroll left tilt
    5: ButtonConfig(ACTION_DPI, 0, DPI_PLUS),                     # DPI+
    6: ButtonConfig(ACTION_DPI, 0, DPI_MINUS),                    # DPI-
}
# Side buttons S1-S12 default to disabled
for i in range(7, TOTAL_BUTTONS):
    DEFAULT_BUTTONS[i] = ButtonConfig.disabled()


def get_all_assignable_keys():
    """Return a sorted list of (display_name, hid_code) for all assignable keys.
    Includes F13-F24."""
    keys = []
    for code, name in sorted(HID_KEY_NAMES.items()):
        if code == HID_KEY_NONE:
            continue
        keys.append((name, code))
    return keys


def get_function_keys():
    """Return just F1-F24 key entries."""
    keys = []
    for n in range(1, 25):
        name = f"F{n}"
        if name in HID_NAME_TO_CODE:
            keys.append((name, HID_NAME_TO_CODE[name]))
    return keys
