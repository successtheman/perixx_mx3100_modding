"""
Perixx MX-3100 Gaming Mouse - HID Protocol Module

Handles low-level HID communication with the mouse via Feature Reports.
Supports reading/writing button configurations including F13-F24 keys.

Device: VID 04D9, PID A11B (Holtek semiconductor chipset)
"""

import ctypes
import ctypes.wintypes as wintypes
import struct
import sys

# ─── Windows HID API bindings ────────────────────────────────────────────────

_hid = ctypes.WinDLL("hid.dll")
_setupapi = ctypes.WinDLL("setupapi.dll")
_kernel32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)

# Constants
DIGCF_PRESENT = 0x02
DIGCF_DEVICEINTERFACE = 0x10
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x01
FILE_SHARE_WRITE = 0x02
OPEN_EXISTING = 3
FILE_FLAG_OVERLAPPED = 0x40000000
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class HIDD_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Size", ctypes.c_ulong),
        ("VendorID", ctypes.c_ushort),
        ("ProductID", ctypes.c_ushort),
        ("VersionNumber", ctypes.c_ushort),
    ]


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("InterfaceClassGuid", GUID),
        ("Flags", ctypes.c_ulong),
        ("Reserved", ctypes.POINTER(ctypes.c_ulong)),
    ]


class OVERLAPPED(ctypes.Structure):
    _fields_ = [
        ("Internal", ctypes.c_void_p),
        ("InternalHigh", ctypes.c_void_p),
        ("Offset", wintypes.DWORD),
        ("OffsetHigh", wintypes.DWORD),
        ("hEvent", ctypes.c_void_p),
    ]


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", ctypes.c_ushort),
        ("UsagePage", ctypes.c_ushort),
        ("InputReportByteLength", ctypes.c_ushort),
        ("OutputReportByteLength", ctypes.c_ushort),
        ("FeatureReportByteLength", ctypes.c_ushort),
        ("Reserved", ctypes.c_ushort * 17),
        ("NumberLinkCollectionNodes", ctypes.c_ushort),
        ("NumberInputButtonCaps", ctypes.c_ushort),
        ("NumberInputValueCaps", ctypes.c_ushort),
        ("NumberInputDataIndices", ctypes.c_ushort),
        ("NumberOutputButtonCaps", ctypes.c_ushort),
        ("NumberOutputValueCaps", ctypes.c_ushort),
        ("NumberOutputDataIndices", ctypes.c_ushort),
        ("NumberFeatureButtonCaps", ctypes.c_ushort),
        ("NumberFeatureValueCaps", ctypes.c_ushort),
        ("NumberFeatureDataIndices", ctypes.c_ushort),
    ]


# ─── 64-bit safe function signatures ─────────────────────────────────────────
# Without explicit restype/argtypes, ctypes defaults to c_int (32-bit) for
# return values and arguments. On 64-bit Windows, HANDLE values are 8 bytes,
# so the default truncates them, causing all subsequent API calls to fail.

_setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
_setupapi.SetupDiGetClassDevsW.argtypes = [
    ctypes.POINTER(GUID), ctypes.c_wchar_p, ctypes.c_void_p, wintypes.DWORD
]
_setupapi.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL
_setupapi.SetupDiEnumDeviceInterfaces.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GUID),
    wintypes.DWORD, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA)
]
_setupapi.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL
_setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
    ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
]
_setupapi.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL
_setupapi.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]

_kernel32.CreateFileW.restype = ctypes.c_void_p
_kernel32.CreateFileW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
    ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p
]
_kernel32.CloseHandle.restype = wintypes.BOOL
_kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
_kernel32.WriteFile.restype = wintypes.BOOL
_kernel32.WriteFile.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
]
_kernel32.ReadFile.restype = wintypes.BOOL
_kernel32.ReadFile.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
]

_kernel32.CreateEventW.restype = ctypes.c_void_p
_kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, ctypes.c_wchar_p]
_kernel32.WaitForSingleObject.restype = wintypes.DWORD
_kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, wintypes.DWORD]
_kernel32.GetOverlappedResult.restype = wintypes.BOOL
_kernel32.GetOverlappedResult.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(OVERLAPPED),
    ctypes.POINTER(wintypes.DWORD), wintypes.BOOL
]
_kernel32.CancelIo.restype = wintypes.BOOL
_kernel32.CancelIo.argtypes = [ctypes.c_void_p]

_hid.HidD_GetHidGuid.argtypes = [ctypes.POINTER(GUID)]
_hid.HidD_GetAttributes.restype = wintypes.BOOL
_hid.HidD_GetAttributes.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDD_ATTRIBUTES)]
_hid.HidD_GetPreparsedData.restype = wintypes.BOOL
_hid.HidD_GetPreparsedData.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
_hid.HidP_GetCaps.restype = ctypes.c_long
_hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]
_hid.HidD_FreePreparsedData.restype = wintypes.BOOL
_hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
_hid.HidD_SetFeature.restype = wintypes.BOOL
_hid.HidD_SetFeature.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.ULONG]
_hid.HidD_GetFeature.restype = wintypes.BOOL
_hid.HidD_GetFeature.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.ULONG]


# ─── Device constants ────────────────────────────────────────────────────────

VID = 0x04D9
PID = 0xA11B


def _get_hid_guid():
    guid = GUID()
    _hid.HidD_GetHidGuid(ctypes.byref(guid))
    return guid


def _open_device(path, overlapped=False):
    flags = FILE_FLAG_OVERLAPPED if overlapped else 0
    handle = _kernel32.CreateFileW(
        path,
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        flags,
        None,
    )
    if handle is None or handle == INVALID_HANDLE_VALUE:
        return None
    return handle


def _close_device(handle):
    if handle is not None and handle != INVALID_HANDLE_VALUE:
        _kernel32.CloseHandle(handle)


def _get_device_caps(handle):
    """Get HID device capabilities (report sizes, usage page, etc.)."""
    ppd = ctypes.c_void_p()
    if not _hid.HidD_GetPreparsedData(handle, ctypes.byref(ppd)):
        return None
    caps = HIDP_CAPS()
    _hid.HidP_GetCaps(ppd, ctypes.byref(caps))
    _hid.HidD_FreePreparsedData(ppd)
    return caps


def enumerate_devices():
    """Find all MX-3100 HID interfaces. Returns list of (path, usage_page, usage, feature_report_len)."""
    guid = _get_hid_guid()
    dev_info = _setupapi.SetupDiGetClassDevsW(
        ctypes.byref(guid), None, None, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
    )
    if dev_info is None or dev_info == INVALID_HANDLE_VALUE:
        return []

    results = []
    index = 0
    while True:
        iface_data = SP_DEVICE_INTERFACE_DATA()
        iface_data.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
        if not _setupapi.SetupDiEnumDeviceInterfaces(
            dev_info, None, ctypes.byref(guid), index, ctypes.byref(iface_data)
        ):
            break
        index += 1

        # Get required size
        required_size = ctypes.c_ulong(0)
        _setupapi.SetupDiGetDeviceInterfaceDetailW(
            dev_info, ctypes.byref(iface_data), None, 0, ctypes.byref(required_size), None
        )

        # Allocate and get detail
        buf = ctypes.create_string_buffer(required_size.value)
        # SP_DEVICE_INTERFACE_DETAIL_DATA_W has cbSize as first field
        ctypes.memmove(buf, struct.pack("I", 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6), 4)
        _setupapi.SetupDiGetDeviceInterfaceDetailW(
            dev_info, ctypes.byref(iface_data), buf, required_size, None, None
        )
        # Path starts at offset 4
        path = ctypes.wstring_at(ctypes.addressof(buf) + 4)

        handle = _open_device(path)
        if handle is None:
            continue

        attrs = HIDD_ATTRIBUTES()
        attrs.Size = ctypes.sizeof(HIDD_ATTRIBUTES)
        if _hid.HidD_GetAttributes(handle, ctypes.byref(attrs)):
            if attrs.VendorID == VID and attrs.ProductID == PID:
                caps = _get_device_caps(handle)
                if caps:
                    results.append((
                        path,
                        caps.UsagePage,
                        caps.Usage,
                        caps.FeatureReportByteLength,
                        caps.InputReportByteLength,
                        caps.OutputReportByteLength,
                    ))

        _close_device(handle)

    _setupapi.SetupDiDestroyDeviceInfoList(dev_info)
    return results


class MX3100Device:
    """HID interface to the Perixx MX-3100 gaming mouse.

    Opens with FILE_FLAG_OVERLAPPED for proper data read/write support.
    Provides methods matching the pzl/mx3100drv protocol:
      send_feature / read_feature  (9-byte feature reports for commands)
      write_data / read_data       (64-byte output/input reports for data)
    """

    def __init__(self, path=None):
        self.handle = None
        self.path = path
        self.feature_report_len = 0
        self.input_report_len = 0
        self.output_report_len = 0
        self.usage_page = 0
        self.usage = 0

    def open(self, path=None):
        """Open the device. If path is None, auto-detect the configuration interface."""
        if path:
            self.path = path

        if self.path:
            self.handle = _open_device(self.path, overlapped=True)
            if self.handle is None:
                raise IOError(f"Cannot open device at {self.path}")
            caps = _get_device_caps(self.handle)
            if caps:
                self.feature_report_len = caps.FeatureReportByteLength
                self.input_report_len = caps.InputReportByteLength
                self.output_report_len = caps.OutputReportByteLength
                self.usage_page = caps.UsagePage
                self.usage = caps.Usage
            return

        # Auto-detect: find the vendor-specific config interface (UsagePage 0xFF00+)
        devices = enumerate_devices()
        if not devices:
            raise IOError(
                "MX-3100 mouse not found. Make sure it's connected and no other "
                "software is using it."
            )

        # Prefer vendor-specific interface (UsagePage >= 0xFF00) with output reports
        vendor_devs = [d for d in devices if d[1] >= 0xFF00 and d[5] > 0]
        if vendor_devs:
            best = vendor_devs[0]
        else:
            # Fallback: largest feature report
            best = max(devices, key=lambda d: d[3])
        self.path = best[0]
        self.usage_page = best[1]
        self.usage = best[2]
        self.feature_report_len = best[3]
        self.input_report_len = best[4]
        self.output_report_len = best[5]

        self.handle = _open_device(self.path, overlapped=True)
        if self.handle is None:
            raise IOError(f"Cannot open device at {self.path}")

    def close(self):
        if self.handle:
            _close_device(self.handle)
            self.handle = None

    # ── Feature reports (9-byte command channel) ────────────────────────────

    def send_feature(self, cmd_8bytes):
        """Send a 9-byte feature report: [ReportID=0x00] + cmd[8]."""
        if not self.handle:
            raise IOError("Device not open")
        buf = (ctypes.c_ubyte * 9)(0, *cmd_8bytes[:8])
        if not _hid.HidD_SetFeature(self.handle, buf, 9):
            raise IOError(f"HidD_SetFeature failed (error {ctypes.get_last_error()})")

    def read_feature(self):
        """Read a 9-byte feature report, return 8-byte command payload."""
        if not self.handle:
            raise IOError("Device not open")
        buf = (ctypes.c_ubyte * 9)(0)
        if not _hid.HidD_GetFeature(self.handle, buf, 9):
            raise IOError(f"HidD_GetFeature failed (error {ctypes.get_last_error()})")
        return list(buf)[1:]  # Strip report ID

    # ── Data reports (64-byte data channel, overlapped I/O) ─────────────────

    def write_data(self, data_64bytes):
        """Write a 65-byte output report (ReportID=0x00 + 64 bytes data)."""
        if not self.handle:
            raise IOError("Device not open")
        buf = (ctypes.c_ubyte * 65)(0, *data_64bytes[:64])
        written = wintypes.DWORD(0)
        ovl = OVERLAPPED()
        evt = _kernel32.CreateEventW(None, True, False, None)
        ovl.hEvent = evt
        try:
            r = _kernel32.WriteFile(self.handle, buf, 65,
                                    ctypes.byref(written), ctypes.byref(ovl))
            if not r:
                err = ctypes.get_last_error()
                if err == 997:  # ERROR_IO_PENDING
                    wait = _kernel32.WaitForSingleObject(evt, 2000)
                    if wait != 0:
                        _kernel32.CancelIo(self.handle)
                        raise IOError("write_data timed out")
                    _kernel32.GetOverlappedResult(
                        self.handle, ctypes.byref(ovl),
                        ctypes.byref(written), True)
                else:
                    raise IOError(f"WriteFile failed (error {err})")
        finally:
            _kernel32.CloseHandle(evt)

    def read_data(self, timeout_ms=2000):
        """Read a 64-byte input report with timeout. Returns list of 64 bytes."""
        if not self.handle:
            raise IOError("Device not open")
        buf = (ctypes.c_ubyte * 65)()
        rd = wintypes.DWORD(0)
        ovl = OVERLAPPED()
        evt = _kernel32.CreateEventW(None, True, False, None)
        ovl.hEvent = evt
        try:
            r = _kernel32.ReadFile(self.handle, buf, 65,
                                   ctypes.byref(rd), ctypes.byref(ovl))
            if not r:
                err = ctypes.get_last_error()
                if err == 997:  # ERROR_IO_PENDING
                    wait = _kernel32.WaitForSingleObject(evt, timeout_ms)
                    if wait != 0:
                        _kernel32.CancelIo(self.handle)
                        return None
                    _kernel32.GetOverlappedResult(
                        self.handle, ctypes.byref(ovl),
                        ctypes.byref(rd), True)
                else:
                    raise IOError(f"ReadFile failed (error {err})")
            return list(buf[1:65])  # Strip report ID byte
        finally:
            _kernel32.CloseHandle(evt)

    # ── Legacy methods (kept for compatibility) ─────────────────────────────

    def set_feature(self, data):
        """Send a raw HID Feature Report."""
        if not self.handle:
            raise IOError("Device not open")
        buf = (ctypes.c_ubyte * len(data))(*data)
        if not _hid.HidD_SetFeature(self.handle, buf, len(data)):
            raise IOError(f"HidD_SetFeature failed (error {ctypes.get_last_error()})")

    def get_feature(self, report_id, length=None):
        """Read a raw HID Feature Report."""
        if not self.handle:
            raise IOError("Device not open")
        if length is None:
            length = self.feature_report_len
        buf = (ctypes.c_ubyte * length)()
        buf[0] = report_id
        if not _hid.HidD_GetFeature(self.handle, buf, length):
            raise IOError(f"HidD_GetFeature failed (error {ctypes.get_last_error()})")
        return list(buf)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()
