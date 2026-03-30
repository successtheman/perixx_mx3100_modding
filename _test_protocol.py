"""Test MX-3100 protocol from pzl/mx3100drv reference implementation."""
import ctypes
import ctypes.wintypes as wintypes

from mx3100_hid import (
    _kernel32, _hid, enumerate_devices,
    GENERIC_READ, GENERIC_WRITE, FILE_SHARE_READ, FILE_SHARE_WRITE,
    OPEN_EXISTING, INVALID_HANDLE_VALUE,
)

FILE_FLAG_OVERLAPPED = 0x40000000

class OVERLAPPED(ctypes.Structure):
    _fields_ = [
        ("Internal", ctypes.c_void_p),
        ("InternalHigh", ctypes.c_void_p),
        ("Offset", wintypes.DWORD),
        ("OffsetHigh", wintypes.DWORD),
        ("hEvent", ctypes.c_void_p),
    ]

_kernel32.CreateEventW.restype = ctypes.c_void_p
_kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, ctypes.c_wchar_p]
_kernel32.WaitForSingleObject.restype = wintypes.DWORD
_kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, wintypes.DWORD]
_kernel32.GetOverlappedResult.restype = wintypes.BOOL
_kernel32.GetOverlappedResult.argtypes = [ctypes.c_void_p, ctypes.POINTER(OVERLAPPED), ctypes.POINTER(wintypes.DWORD), wintypes.BOOL]
_kernel32.CancelIo.restype = wintypes.BOOL
_kernel32.CancelIo.argtypes = [ctypes.c_void_p]

# Protocol constants from pzl/mx3100drv
CMD_MSG_LEN = 8
DATA_LINE_LEN = 64
SECTION_LEN = DATA_LINE_LEN * 2  # 128 bytes

CONFIGS_ADDR = 0x73
BUTTONS_ADDR = 0x72
SETTINGS_ADDR_MAX = 0x73
SETTINGS_ADDR_PARITY = 0x0C
ADDR_READ = 0x80


def fmt(data, n=64):
    return " ".join(f"{b:02X}" for b in data[:n])


def open_device():
    devs = enumerate_devices()
    vdevs = [d for d in devs if d[1] >= 0xFF00 and d[5] > 0]
    if not vdevs:
        print("No vendor interface found")
        return None, None
    path = vdevs[0][0]
    h = _kernel32.CreateFileW(
        path, GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None, OPEN_EXISTING, FILE_FLAG_OVERLAPPED, None,
    )
    if h is None or h == INVALID_HANDLE_VALUE:
        print("Cannot open device")
        return None, None
    return h, path


def send_feature(handle, cmd_8bytes):
    """Send 9-byte feature report: [0x00] + cmd[8]"""
    buf = (ctypes.c_ubyte * 9)(0, *cmd_8bytes)
    result = _hid.HidD_SetFeature(handle, buf, 9)
    if not result:
        print(f"  SetFeature FAILED err={ctypes.get_last_error()}")
        return False
    return True


def read_feature(handle):
    """Read 9-byte feature report, return 8-byte command response."""
    buf = (ctypes.c_ubyte * 9)(0)
    result = _hid.HidD_GetFeature(handle, buf, 9)
    if not result:
        print(f"  GetFeature FAILED err={ctypes.get_last_error()}")
        return None
    return list(buf)[1:]  # Strip report ID


def write_data(handle, data_64bytes):
    """Write 65-byte output report (report ID 0x00 + 64 bytes data)."""
    buf = (ctypes.c_ubyte * 65)(0, *data_64bytes[:64])
    written = wintypes.DWORD(0)
    ovl = OVERLAPPED()
    evt = _kernel32.CreateEventW(None, True, False, None)
    ovl.hEvent = evt
    r = _kernel32.WriteFile(handle, buf, 65, ctypes.byref(written), ctypes.byref(ovl))
    if not r:
        err = ctypes.get_last_error()
        if err == 997:
            _kernel32.WaitForSingleObject(evt, 2000)
            _kernel32.GetOverlappedResult(handle, ctypes.byref(ovl), ctypes.byref(written), True)
        else:
            print(f"  WriteFile error: {err}")
            _kernel32.CloseHandle(evt)
            return False
    _kernel32.CloseHandle(evt)
    return True


def read_data(handle, timeout_ms=2000):
    """Read 64-byte input report with timeout."""
    buf = (ctypes.c_ubyte * 65)()
    rd = wintypes.DWORD(0)
    ovl = OVERLAPPED()
    evt = _kernel32.CreateEventW(None, True, False, None)
    ovl.hEvent = evt
    r = _kernel32.ReadFile(handle, buf, 65, ctypes.byref(rd), ctypes.byref(ovl))
    if not r:
        err = ctypes.get_last_error()
        if err == 997:
            w = _kernel32.WaitForSingleObject(evt, timeout_ms)
            if w == 0:
                _kernel32.GetOverlappedResult(handle, ctypes.byref(ovl), ctypes.byref(rd), True)
                _kernel32.CloseHandle(evt)
                return list(buf[1:65])  # Strip report ID byte
            else:
                _kernel32.CancelIo(handle)
                _kernel32.CloseHandle(evt)
                return None
        else:
            print(f"  ReadFile error: {err}")
            _kernel32.CloseHandle(evt)
            return None
    _kernel32.CloseHandle(evt)
    return list(buf[1:65])


def read_section(handle, addr):
    """Read a 128-byte section from mouse memory."""
    cmd = [0] * CMD_MSG_LEN
    cmd[7] = addr

    if addr == CONFIGS_ADDR or addr == BUTTONS_ADDR:
        cmd[0] = ADDR_READ | (SETTINGS_ADDR_MAX - addr + SETTINGS_ADDR_PARITY)
    else:
        cmd[0] = ADDR_READ | 0x0F  # MACRO_MEM_FLAG
        cmd[1] = 0x70 - addr       # MACRO_ADDR_PARITY - addr

    print(f"  CMD: {fmt(cmd, 8)}")
    if not send_feature(handle, cmd):
        return None

    ack = read_feature(handle)
    if ack:
        print(f"  ACK: {fmt(ack, 8)}")
    else:
        print("  ACK: failed")
        return None

    data1 = read_data(handle)
    if data1 is None:
        print("  DATA1: timeout")
        return None
    print(f"  DATA1: {fmt(data1, 32)}...")

    data2 = read_data(handle)
    if data2 is None:
        print("  DATA2: timeout")
        return None
    print(f"  DATA2: {fmt(data2, 32)}...")

    return data1 + data2


def main():
    handle, path = open_device()
    if not handle:
        return

    print("=== Sending startup commands ===")
    start1 = [0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFD]
    start2 = [0x03, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0xFA]

    print("Start1:", fmt(start1, 8))
    ok1 = send_feature(handle, start1)
    print(f"  Result: {ok1}")

    print("Start2:", fmt(start2, 8))
    ok2 = send_feature(handle, start2)
    print(f"  Result: {ok2}")
    print()

    # Read config section
    print("=== Reading CONFIGS (addr=0x73) ===")
    config = read_section(handle, CONFIGS_ADDR)
    if config:
        print(f"\n  Full config ({len(config)} bytes):")
        for off in range(0, len(config), 16):
            chunk = config[off:off+16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            print(f"    {off:04X}: {hex_part}")
    print()

    # Read buttons section
    print("=== Reading BUTTONS (addr=0x72) ===")
    buttons = read_section(handle, BUTTONS_ADDR)
    if buttons:
        print(f"\n  Full buttons ({len(buttons)} bytes):")
        for off in range(0, len(buttons), 16):
            chunk = buttons[off:off+16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            print(f"    {off:04X}: {hex_part}")

        # Parse button assignments (4 bytes per button)
        print("\n  Button assignments:")
        for i in range(0, min(len(buttons), 19*4), 4):
            b = buttons[i:i+4]
            btn_idx = i // 4
            print(f"    Button {btn_idx:2d}: {fmt(b, 4)}")
    print()

    _kernel32.CloseHandle(handle)
    print("Done.")


if __name__ == "__main__":
    main()
