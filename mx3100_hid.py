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
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value


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


# ─── Device constants ────────────────────────────────────────────────────────

VID = 0x04D9
PID = 0xA11B


def _get_hid_guid():
    guid = GUID()
    _hid.HidD_GetHidGuid(ctypes.byref(guid))
    return guid


def _open_device(path):
    handle = _kernel32.CreateFileW(
        path,
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        0,
        None,
    )
    if handle == INVALID_HANDLE_VALUE:
        return None
    return handle


def _close_device(handle):
    if handle and handle != INVALID_HANDLE_VALUE:
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
    if dev_info == INVALID_HANDLE_VALUE:
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
    """HID interface to the Perixx MX-3100 gaming mouse."""

    def __init__(self, path=None):
        self.handle = None
        self.path = path
        self.feature_report_len = 0
        self.usage_page = 0
        self.usage = 0

    def open(self, path=None):
        """Open the device. If path is None, auto-detect the configuration interface."""
        if path:
            self.path = path

        if self.path:
            self.handle = _open_device(self.path)
            if self.handle is None:
                raise IOError(f"Cannot open device at {self.path}")
            caps = _get_device_caps(self.handle)
            if caps:
                self.feature_report_len = caps.FeatureReportByteLength
                self.usage_page = caps.UsagePage
                self.usage = caps.Usage
            return

        # Auto-detect: find the interface that supports feature reports
        devices = enumerate_devices()
        if not devices:
            raise IOError(
                "MX-3100 mouse not found. Make sure it's connected and no other "
                "software is using it."
            )

        # Prefer the interface with the largest feature report (that's the config one)
        best = max(devices, key=lambda d: d[3])
        self.path = best[0]
        self.usage_page = best[1]
        self.usage = best[2]
        self.feature_report_len = best[3]

        self.handle = _open_device(self.path)
        if self.handle is None:
            raise IOError(f"Cannot open device at {self.path}")

    def close(self):
        if self.handle:
            _close_device(self.handle)
            self.handle = None

    def set_feature(self, data):
        """Send a HID Feature Report to the device."""
        if not self.handle:
            raise IOError("Device not open")
        buf = (ctypes.c_ubyte * len(data))(*data)
        result = _hid.HidD_SetFeature(self.handle, buf, len(data))
        if not result:
            raise IOError(f"HidD_SetFeature failed (error {ctypes.get_last_error()})")
        return True

    def get_feature(self, report_id, length=None):
        """Read a HID Feature Report from the device."""
        if not self.handle:
            raise IOError("Device not open")
        if length is None:
            length = self.feature_report_len
        buf = (ctypes.c_ubyte * length)()
        buf[0] = report_id
        result = _hid.HidD_GetFeature(self.handle, buf, length)
        if not result:
            raise IOError(f"HidD_GetFeature failed (error {ctypes.get_last_error()})")
        return list(buf)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()
