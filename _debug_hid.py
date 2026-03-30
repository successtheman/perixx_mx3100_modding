"""Quick diagnostic for HID enumeration."""
import ctypes
import ctypes.wintypes as wintypes
import struct

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8),
    ]

class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong), ("InterfaceClassGuid", GUID),
        ("Flags", ctypes.c_ulong), ("Reserved", ctypes.POINTER(ctypes.c_ulong)),
    ]

class HIDD_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Size", ctypes.c_ulong), ("VendorID", ctypes.c_ushort),
        ("ProductID", ctypes.c_ushort), ("VersionNumber", ctypes.c_ushort),
    ]

class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", ctypes.c_ushort), ("UsagePage", ctypes.c_ushort),
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

_hid = ctypes.WinDLL("hid.dll")
_setupapi = ctypes.WinDLL("setupapi.dll")
_kernel32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)

# CRITICAL: Set proper return types for 64-bit compatibility
_setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
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
_kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
_hid.HidD_GetAttributes.restype = wintypes.BOOL
_hid.HidD_GetAttributes.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDD_ATTRIBUTES)]
_hid.HidD_GetPreparsedData.restype = wintypes.BOOL
_hid.HidD_GetPreparsedData.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
_hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]
_hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]

DIGCF_PRESENT = 0x02
DIGCF_DEVICEINTERFACE = 0x10
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
OPEN_EXISTING = 3
INVALID_HANDLE = ctypes.c_void_p(-1).value

guid = GUID()
_hid.HidD_GetHidGuid(ctypes.byref(guid))
d4 = bytes(guid.Data4)
print(f"HID GUID: {{{guid.Data1:08X}-{guid.Data2:04X}-{guid.Data3:04X}-{d4[0]:02X}{d4[1]:02X}-{d4[2]:02X}{d4[3]:02X}{d4[4]:02X}{d4[5]:02X}{d4[6]:02X}{d4[7]:02X}}}")

dev_info = _setupapi.SetupDiGetClassDevsW(
    ctypes.byref(guid), None, None, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
)
print(f"DevInfo handle: {dev_info:#018x}")
print(f"Is invalid: {dev_info == INVALID_HANDLE}")
print()

index = 0
total = 0
matches = 0

while index < 500:
    iface = SP_DEVICE_INTERFACE_DATA()
    iface.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
    ok = _setupapi.SetupDiEnumDeviceInterfaces(
        dev_info, None, ctypes.byref(guid), index, ctypes.byref(iface)
    )
    if not ok:
        err = ctypes.get_last_error()
        if index == 0:
            print(f"SetupDiEnumDeviceInterfaces failed on first call, error={err}")
        break
    index += 1
    total += 1

    req = wintypes.DWORD(0)
    _setupapi.SetupDiGetDeviceInterfaceDetailW(
        dev_info, ctypes.byref(iface), None, 0, ctypes.byref(req), None
    )
    buf = ctypes.create_string_buffer(req.value)
    # SP_DEVICE_INTERFACE_DETAIL_DATA_W.cbSize
    cb = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
    ctypes.memmove(buf, struct.pack("I", cb), 4)
    if not _setupapi.SetupDiGetDeviceInterfaceDetailW(
        dev_info, ctypes.byref(iface), buf, req, None, None
    ):
        continue
    path = ctypes.wstring_at(ctypes.addressof(buf) + 4)

    if "04d9" in path.lower() and "a11b" in path.lower():
        matches += 1
        print(f"--- MX-3100 Interface #{matches} ---")
        print(f"  Path: {path}")

        # Try open with R/W
        h = _kernel32.CreateFileW(
            path, GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None, OPEN_EXISTING, 0, None
        )
        if h is None or h == INVALID_HANDLE:
            err = ctypes.get_last_error()
            print(f"  R/W open FAILED (error {err})")
            # Try zero-access (just for attributes)
            h = _kernel32.CreateFileW(
                path, 0, FILE_SHARE_READ | FILE_SHARE_WRITE,
                None, OPEN_EXISTING, 0, None
            )
            if h is None or h == INVALID_HANDLE:
                print(f"  Zero-access open ALSO FAILED (error {ctypes.get_last_error()})")
                continue
            print(f"  Zero-access open OK")

        attrs = HIDD_ATTRIBUTES()
        attrs.Size = ctypes.sizeof(HIDD_ATTRIBUTES)
        _hid.HidD_GetAttributes(h, ctypes.byref(attrs))
        print(f"  VID={attrs.VendorID:04X} PID={attrs.ProductID:04X} Ver={attrs.VersionNumber}")

        ppd = ctypes.c_void_p()
        if _hid.HidD_GetPreparsedData(h, ctypes.byref(ppd)):
            caps = HIDP_CAPS()
            _hid.HidP_GetCaps(ppd, ctypes.byref(caps))
            print(f"  UsagePage=0x{caps.UsagePage:04X} Usage=0x{caps.Usage:04X}")
            print(f"  FeatureReportLen={caps.FeatureReportByteLength}")
            print(f"  InputReportLen={caps.InputReportByteLength}")
            print(f"  OutputReportLen={caps.OutputReportByteLength}")
            _hid.HidD_FreePreparsedData(ppd)
        else:
            print(f"  GetPreparsedData FAILED")

        _kernel32.CloseHandle(h)
        print()

print(f"Total HID interfaces: {total}")
print(f"MX-3100 matches: {matches}")
_setupapi.SetupDiDestroyDeviceInfoList(dev_info)
