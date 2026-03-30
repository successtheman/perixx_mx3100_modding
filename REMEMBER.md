# MX-3100 Project - Remember Doc

Key findings, gotchas, and reference info accumulated during reverse-engineering.

---

## Hardware

- **Mouse**: Perixx MX-3100 Gaming Mouse
- **Chipset**: Holtek HT68FB5x0
- **USB IDs**: VID `0x04D9`, PID `0xA11B`
- **Original installer**: Inno Setup (not Delphi) wrapping an MFC C++ app (VS2008)
- **HID Interfaces**: 7 total enumerated, 4 openable from our code:
  - Interface 0 (mi_02): **Vendor-specific** — UsagePage=0xFF00, Feature=9B, Input=65B, Output=65B — **THIS IS THE CONFIG INTERFACE**
  - Interface 1: Generic Desktop (0x0001), Usage=0x0080 — system control
  - Interface 2: Consumer (0x000C) — media keys
  - Interface 3: Vendor 0xFF01 — unknown

## Critical Bug: 64-bit ctypes Handle Truncation

**Problem**: On 64-bit Windows, `ctypes` defaults `restype` to `c_int` (4 bytes). Windows HANDLE values are 8 bytes on x64, so `SetupDiGetClassDevsW` return values get silently truncated, causing all subsequent API calls to fail.

**Fix**: Explicitly set `restype = ctypes.c_void_p` for every function that returns a handle:
```python
_setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
_kernel32.CreateFileW.restype = ctypes.c_void_p
_kernel32.CreateEventW.restype = ctypes.c_void_p
```
Also set `INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value` (not `wintypes.HANDLE(-1).value`).

## Protocol (from pzl/mx3100drv reference implementation)

### Communication Channels
| Channel  | Report Size | Method             | Purpose           |
|----------|-------------|---------------------|-------------------|
| Control  | 9 bytes     | HidD_SetFeature / HidD_GetFeature | Commands & ACKs |
| Data     | 65 bytes    | WriteFile / ReadFile (overlapped) | Bulk data transfer |

Feature report = `[ReportID=0x00] + [8-byte command]`
Data report = `[ReportID=0x00] + [64-byte payload]`

### Startup Sequence
Two feature reports must be sent before any read/write:
```
CMD1: 02 00 00 00 00 00 00 FD
CMD2: 03 00 02 00 00 00 00 FA  (poll rate related)
```

### Memory Map
| Address | Content   | Size    |
|---------|-----------|---------|
| 0x73    | Settings (DPI, LED, sensitivity) | 128 bytes |
| 0x72    | Button mappings (19 buttons)     | 128 bytes |
| 0x6F↓   | Macros (19 slots, descending)    | 128 bytes each |

### Read Section (addr)
```
cmd[0] = 0x80 | (0x73 - addr + 0x0C)   # 0x8C for configs, 0x8D for buttons
cmd[7] = addr
→ send_feature(cmd)
→ read_feature() [ACK]
→ read_data() × 2 [128 bytes total]
```

### Write Section (addr)
```
cmd[0] = 0x73 - addr + 0x0C             # 0x0C for configs, 0x0D for buttons
cmd[2] = 128                             # section length
cmd[7] = addr
→ send_feature(cmd)
→ write_data() × 2 [128 bytes total]
```

### Button Format (4 bytes each)
```
[btn_type, modifier, key_code, extra]
```

| btn_type | Meaning     | key_code examples |
|----------|-------------|-------------------|
| 0x00     | Keyboard    | HID usage code (0x00 = disabled) |
| 0x01     | Mouse       | 0xF0=LMB, 0xF1=RMB, 0xF2=MMB, 0xF5=Back, 0xF6=Fwd, 0xF7=ScrollUp, 0xF8=ScrollDn |
| 0x03     | Multimedia  | Consumer usage code (0xCD=Play/Pause, 0xE9=VolUp, etc.) |
| 0x07     | DPI         | 0x01=DPI+, 0x02=DPI-, 0x03=DPI Loop |

### Factory Default Buttons (confirmed from live read)
```
Btn  0: 01 00 F0 00  Left Click
Btn  1: 01 00 F1 00  Right Click
Btn  2: 01 00 F2 00  Middle Click
Btn  3: 07 00 01 00  DPI+
Btn  4: 07 00 02 00  DPI-
Btn  5: 01 00 F5 00  Back
Btn  6: 01 00 F6 00  Forward
Btn  7: 00 00 00 00  Disabled
Btn  8: 00 00 00 00  Disabled
...
Btn 14: 01 00 F7 00  Scroll Up
Btn 15: 01 00 F8 00  Scroll Down
...
```

### F13-F24 Key Codes
To assign F13-F24, use `btn_type=0x00` (keyboard), `key_code` = HID usage:
```
F13=0x68  F14=0x69  F15=0x6A  F16=0x6B
F17=0x6C  F18=0x6D  F19=0x6E  F20=0x6F
F21=0x70  F22=0x71  F23=0x72  F24=0x73
```
Example: Assign F13 to button 7 → write `[0x00, 0x00, 0x68, 0x00]` at offset 28 (7×4).

### Config Section Offsets (within 128-byte settings section @ 0x73)
| Offset | Setting |
|--------|---------|
| 0x31   | Angle Correction |
| 0x33   | Angle Snap |
| 0x47   | LED Mode (0=off, 1=standard, 2=breathe, 3=neon) |
| 0x48   | LED Config (brightness/speed) |
| 0x4A   | Sensitivity X |
| 0x4B   | Sensitivity Y |
| 0x54-0x5B | DPI X values (7 profiles) |
| 0x5C-0x63 | DPI Y values (7 profiles) |
| 0x64   | DPI Enable flags (bit per profile) |
| 0x68+  | DPI Colors (3 bytes per profile) |

## Overlapped I/O

The data channel (WriteFile/ReadFile) **requires** overlapped I/O on Windows. Without it, reads block indefinitely because the mouse only sends data after a feature report command triggers it.

Pattern:
```python
ovl = OVERLAPPED()
evt = CreateEventW(None, True, False, None)
ovl.hEvent = evt
ReadFile(handle, buf, 65, byref(rd), byref(ovl))
# If ERROR_IO_PENDING (997):
WaitForSingleObject(evt, timeout_ms)
GetOverlappedResult(handle, byref(ovl), byref(rd), True)
```

## File Structure
| File | Purpose |
|------|---------|
| `mx3100_hid.py` | Low-level Windows HID API bindings (ctypes), device enumeration, overlapped I/O |
| `mx3100_protocol.py` | Button types, HID key codes, protocol constants, ButtonConfig class |
| `mx3100_tool.py` | Main app: GUI (tkinter) + CLI, protocol layer (read/write sections) |
| `mx3100_sniffer.py` | HID protocol sniffer for reverse-engineering |
| `_test_protocol.py` | Standalone protocol test (confirmed working) |
| `_debug_hid.py` | Diagnostic that proved the 64-bit ctypes bug |
| `_probe_protocol.py` | Early protocol probing (output reports alone don't work) |

## Reference Implementation
- **pzl/mx3100drv** (GitHub): C implementation for same mouse, uses hidapi
- Our Python port confirmed working against the same protocol

## Things That Don't Work
- Sending output reports without a preceding feature report command = no response
- Feature reports alone only return `[ID, 0x01, 0x00...]` (status bytes, not config data)
- Non-overlapped ReadFile blocks forever waiting for input that never comes
- The original driver's protocol is NOT simple feature-report-based; it's a command+data pipeline
