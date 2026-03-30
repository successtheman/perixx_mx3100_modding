# Perixx MX-3100 Gaming Mouse Configurator

A replacement configuration tool for the Perixx MX-3100 gaming mouse that adds support for **F13-F24** key assignments — something the original driver software doesn't offer.

## What This Does

The original MX-3100 driver (`MX-3100.exe`) only lets you assign keys from a standard keyboard (up to F12). This tool communicates with the same mouse hardware over USB HID and adds:

- **F13-F24 key assignments** for all 19 mouse buttons
- Modifier combo support (Ctrl/Shift/Alt/Win + any key)
- Profile save/load (JSON format)
- HID protocol sniffer for reverse-engineering
- Both GUI and command-line interfaces

## Hardware Info

| Property | Value |
|----------|-------|
| Device | Perixx MX-3100 Gaming Mouse |
| USB VID | `04D9` (Holtek Semiconductor) |
| USB PID | `A11B` |
| Chipset | Holtek HT68FB5x0 series |
| Buttons | 7 front + 12 side = 19 total |
| Protocol | HID Feature Reports (Set/Get) |

## Requirements

- **Windows** (uses native HID API via ctypes)
- **Python 3.7+**
- **Administrator privileges** (required for HID device access)
- The mouse must be connected via USB

No pip packages needed — the tool uses only the Windows HID API directly through ctypes.

## Quick Start

### 1. Discover the Protocol (First Time Setup)

The exact HID report format varies between firmware versions. Run the sniffer first to discover it:

```powershell
# Run as Administrator!
python mx3100_sniffer.py              # List HID interfaces
python mx3100_sniffer.py --probe      # Find valid report IDs
python mx3100_sniffer.py --dump 0x07  # Dump a specific report
python mx3100_sniffer.py --watch      # Watch for changes while using original software
```

The `--watch` mode is especially useful: run it while using the original MX-3100 software to make button changes, and it will show you exactly which bytes change.

### 2. Update Protocol Constants (If Needed)

If the sniffer reveals different report IDs than the defaults, update these constants at the top of `mx3100_tool.py`:

```python
REPORT_ID_CONFIG = 0x07     # Change if different
CMD_READ_BUTTONS = 0x05     # Change if different
CMD_WRITE_BUTTONS = 0x06    # Change if different
CMD_SAVE = 0x09             # Change if different
```

### 3. Launch the GUI

```powershell
python mx3100_tool.py
```

### 4. Or Use the CLI

```powershell
# Detect the mouse
python mx3100_tool.py --detect

# List all assignable keys (including F13-F24)
python mx3100_tool.py --list-keys

# Assign F13 to side button S1 (button index 7)
python mx3100_tool.py --assign 7 F13

# Assign Ctrl+F20 to side button S5 (button index 11)
python mx3100_tool.py --assign 11 F20 --modifier ctrl
```

## Button Index Reference

| Index | Button | Default Function |
|-------|--------|-----------------|
| 0 | Button 1 | Left Click |
| 1 | Button 2 | Right Click |
| 2 | Button 3 | Scroll Click |
| 3 | Button 4 | Scroll Right Tilt |
| 4 | Button 5 | Scroll Left Tilt |
| 5 | Button 6 | DPI + |
| 6 | Button 7 | DPI - |
| 7 | Side Button S1 | Disabled |
| 8 | Side Button S2 | Disabled |
| 9 | Side Button S3 | Disabled |
| 10 | Side Button S4 | Disabled |
| 11 | Side Button S5 | Disabled |
| 12 | Side Button S6 | Disabled |
| 13 | Side Button S7 | Disabled |
| 14 | Side Button S8 | Disabled |
| 15 | Side Button S9 | Disabled |
| 16 | Side Button S10 | Disabled |
| 17 | Side Button S11 | Disabled |
| 18 | Side Button S12 | Disabled |

## F13-F24 HID Usage Codes

| Key | HID Code | Windows VK |
|-----|----------|-----------|
| F13 | `0x68` | `VK_F13` (0x7C) |
| F14 | `0x69` | `VK_F14` (0x7D) |
| F15 | `0x6A` | `VK_F15` (0x7E) |
| F16 | `0x6B` | `VK_F16` (0x7F) |
| F17 | `0x6C` | `VK_F17` (0x80) |
| F18 | `0x6D` | `VK_F18` (0x81) |
| F19 | `0x6E` | `VK_F19` (0x82) |
| F20 | `0x6F` | `VK_F20` (0x83) |
| F21 | `0x70` | `VK_F21` (0x84) |
| F22 | `0x71` | `VK_F22` (0x85) |
| F23 | `0x72` | `VK_F23` (0x86) |
| F24 | `0x73` | `VK_F24` (0x87) |

## File Structure

```
├── mx3100_tool.py        # Main GUI + CLI application
├── mx3100_hid.py         # Low-level Windows HID API bindings
├── mx3100_protocol.py    # Protocol constants, key codes, button definitions
├── mx3100_sniffer.py     # HID protocol sniffer/reverse-engineering tool
├── requirements.txt      # Python dependencies (none required for core)
├── profiles/             # Saved button profiles (JSON)
└── extracted/            # Original driver files (from Inno Setup installer)
    ├── pf64/MX-3100/     # 64-bit driver + resources
    └── pf32/MX-3100/     # 32-bit driver + resources
```

## How It Works

1. The tool enumerates USB HID devices to find the MX-3100 (VID `04D9`, PID `A11B`)
2. It opens the HID interface that supports Feature Reports (the configuration interface)
3. Button assignments are sent via `HidD_SetFeature` as structured byte arrays
4. Each button gets 5 bytes: `[action_type, modifier, key_code, extra1, extra2]`
5. For keyboard keys: action_type=`0x01`, modifier=HID modifier flags, key_code=HID usage code
6. F13-F24 use HID usage codes `0x68`-`0x73` (USB HID Usage Tables, Keyboard Page 0x07)

## Reverse Engineering Notes

The original driver was extracted from an Inno Setup installer. Key findings:

- **Framework**: MFC C++ (Visual Studio 2008) — `AfxWnd90su` window classes
- **HID APIs used**: `HidD_SetFeature`, `HidD_GetFeature`, `HidD_GetAttributes`, `HidD_GetPreparsedData`
- **Firmware chipset**: Holtek HT68FB5x0 (confirmed by EFORMAT.INI in firmware update tool)
- **Key capture**: Windows keyboard hooks (`KeyboardHook_SingleDlgKey`, `KeyboardHook_ComboDlg`)
- **Config storage**: INI files (`config0.ini`-`config5.ini` for 6 profiles, `str*.ini` for localized strings)
- **Limitation**: Original keyboard hook can't capture F13-F24 since no physical keys exist for them

The original software's key assignment dialog uses a keyboard hook to capture keystrokes. Since F13-F24 keys don't exist on standard keyboards, the hook never captures them. Our tool bypasses this by directly constructing the HID usage codes and sending them via Feature Reports.

## Troubleshooting

**"Mouse not found"**
- Make sure the mouse is connected via USB (not wireless/Bluetooth)
- Run as Administrator
- Close the original MX-3100 driver software
- Try unplugging and reconnecting the mouse

**"HidD_SetFeature failed"**
- Run as Administrator
- Close any other mouse configuration software  
- The report format might need adjustment — use the sniffer to discover the correct format

**Settings don't take effect**
- The protocol constants may need updating for your firmware version
- Run `python mx3100_sniffer.py --probe` to find the correct report IDs
- Run `python mx3100_sniffer.py --watch` while using the original software to see the exact byte format

## License

This is a community reverse-engineering project for personal use. Not affiliated with Perixx.
