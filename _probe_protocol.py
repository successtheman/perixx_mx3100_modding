"""Probe MX-3100 output/input report protocol with overlapped I/O."""
import ctypes
import ctypes.wintypes as wintypes
from mx3100_hid import (
    _kernel32, enumerate_devices,
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
_kernel32.CreateEventW.argtypes = [
    ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, ctypes.c_wchar_p
]
_kernel32.WaitForSingleObject.restype = wintypes.DWORD
_kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, wintypes.DWORD]
_kernel32.GetOverlappedResult.restype = wintypes.BOOL
_kernel32.GetOverlappedResult.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(OVERLAPPED),
    ctypes.POINTER(wintypes.DWORD), wintypes.BOOL,
]
_kernel32.CancelIo.restype = wintypes.BOOL
_kernel32.CancelIo.argtypes = [ctypes.c_void_p]


def do_write(h, data, length):
    buf = (ctypes.c_ubyte * length)(*([0] * length))
    for i, b in enumerate(data):
        if i < length:
            buf[i] = b
    written = wintypes.DWORD(0)
    ovl = OVERLAPPED()
    evt = _kernel32.CreateEventW(None, True, False, None)
    ovl.hEvent = evt
    r = _kernel32.WriteFile(h, buf, length, ctypes.byref(written), ctypes.byref(ovl))
    if not r:
        err = ctypes.get_last_error()
        if err == 997:  # IO_PENDING
            _kernel32.WaitForSingleObject(evt, 2000)
            _kernel32.GetOverlappedResult(
                h, ctypes.byref(ovl), ctypes.byref(written), True
            )
        else:
            print(f"  WriteFile error: {err}")
            _kernel32.CloseHandle(evt)
            return False
    _kernel32.CloseHandle(evt)
    return True


def do_read(h, length, timeout_ms=500):
    buf = (ctypes.c_ubyte * length)()
    rd = wintypes.DWORD(0)
    ovl = OVERLAPPED()
    evt = _kernel32.CreateEventW(None, True, False, None)
    ovl.hEvent = evt
    r = _kernel32.ReadFile(h, buf, length, ctypes.byref(rd), ctypes.byref(ovl))
    if not r:
        err = ctypes.get_last_error()
        if err == 997:  # IO_PENDING
            w = _kernel32.WaitForSingleObject(evt, timeout_ms)
            if w == 0:  # WAIT_OBJECT_0
                _kernel32.GetOverlappedResult(
                    h, ctypes.byref(ovl), ctypes.byref(rd), True
                )
                _kernel32.CloseHandle(evt)
                return list(buf)
            else:
                _kernel32.CancelIo(h)
                _kernel32.CloseHandle(evt)
                return None
        else:
            print(f"  ReadFile error: {err}")
            _kernel32.CloseHandle(evt)
            return None
    _kernel32.CloseHandle(evt)
    return list(buf)


def fmt(data, n=32):
    return " ".join(f"{b:02X}" for b in data[:n])


def main():
    devs = enumerate_devices()
    vdevs = [d for d in devs if d[1] >= 0xFF00 and d[5] > 0]
    if not vdevs:
        print("No vendor-specific interface found")
        return

    path, up, u, feat, in_len, out_len = vdevs[0]
    print(f"Interface: UP=0x{up:04X} U=0x{u:04X} Feat={feat} In={in_len} Out={out_len}")

    h = _kernel32.CreateFileW(
        path, GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None, OPEN_EXISTING, FILE_FLAG_OVERLAPPED, None,
    )
    if h is None or h == INVALID_HANDLE_VALUE:
        print("Cannot open device")
        return

    print("Opened OK\n")

    # Drain any pending input
    print("=== Draining pending reports ===")
    for i in range(5):
        r = do_read(h, in_len, 100)
        if r and any(b != 0 for b in r):
            print(f"  [{i}]: {fmt(r)}")
        else:
            break
    print()

    # Try various output report commands
    commands = [
        # Format: (description, output_bytes)
        ("0x00 ping", [0x00]),
        ("0x00 0x01 get info", [0x00, 0x01]),
        ("0x00 0x02 get info", [0x00, 0x02]),
        ("0x00 0x04 0x01 read btns", [0x00, 0x04, 0x01, 0x00]),
        ("0x00 0x05 read DPI", [0x00, 0x05, 0x00]),
        ("0x00 0x06 get config", [0x00, 0x06]),
        ("0x00 0x07 query", [0x00, 0x07]),
        ("0x00 0x80 get ver", [0x00, 0x80]),
        ("0x00 0x81 get fw", [0x00, 0x81]),
        ("0x00 0x12 get macro", [0x00, 0x12, 0x00]),
        ("0x00 0x90 dump", [0x00, 0x90]),
        ("0x00 0xFF status", [0x00, 0xFF]),
    ]

    for desc, data in commands:
        send_hex = " ".join(f"{b:02X}" for b in data)
        print(f"--- {desc} [{send_hex}] ---")
        ok = do_write(h, data, out_len)
        if not ok:
            print("  WRITE FAILED")
            continue
        resp = do_read(h, in_len, 500)
        if resp:
            if any(b != 0 for b in resp):
                print(f"  RESP: {fmt(resp)}")
            else:
                print("  (all zeros)")
        else:
            print("  (timeout)")
        print()

    _kernel32.CloseHandle(h)
    print("Done.")


if __name__ == "__main__":
    main()
