"""
Perixx MX-3100 Gaming Mouse - HID Protocol Sniffer

Run this tool to discover the exact HID report format used by the mouse.
It enumerates all HID interfaces and lets you send/receive feature reports
to reverse-engineer the protocol.

Usage:
    python mx3100_sniffer.py              # List all mouse HID interfaces
    python mx3100_sniffer.py --probe      # Probe all possible report IDs
    python mx3100_sniffer.py --dump N     # Dump feature report with ID N
    python mx3100_sniffer.py --watch      # Watch for raw feature changes

Run as Administrator for HID access.
"""

import argparse
import sys
import time
from mx3100_hid import enumerate_devices, MX3100Device


def cmd_list():
    """List all HID interfaces for the MX-3100 mouse."""
    print("Searching for MX-3100 mouse (VID:04D9, PID:A11B)...\n")
    devices = enumerate_devices()
    if not devices:
        print("ERROR: Mouse not found. Make sure it's plugged in and you're "
              "running as Administrator.")
        return

    print(f"Found {len(devices)} HID interface(s):\n")
    for i, (path, usage_page, usage, feat_len, in_len, out_len) in enumerate(devices):
        print(f"  Interface #{i}:")
        print(f"    Path:                {path}")
        print(f"    Usage Page:          0x{usage_page:04X}")
        print(f"    Usage:               0x{usage:04X}")
        print(f"    Feature Report Size: {feat_len} bytes")
        print(f"    Input Report Size:   {in_len} bytes")
        print(f"    Output Report Size:  {out_len} bytes")
        print()

    print("The interface with the largest Feature Report Size is likely the")
    print("configuration interface (for button/DPI/macro settings).")


def cmd_probe(interface_idx=None):
    """Probe all report IDs to find valid feature reports."""
    devices = enumerate_devices()
    if not devices:
        print("ERROR: Mouse not found.")
        return

    if interface_idx is not None:
        targets = [devices[interface_idx]]
    else:
        targets = devices

    for path, usage_page, usage, feat_len, in_len, out_len in targets:
        print(f"\nProbing interface UsagePage=0x{usage_page:04X}, "
              f"Usage=0x{usage:04X}, FeatureLen={feat_len}...")
        dev = MX3100Device(path)
        try:
            dev.open(path)
        except IOError as e:
            print(f"  Cannot open: {e}")
            continue

        found = []
        for report_id in range(256):
            try:
                data = dev.get_feature(report_id, feat_len)
                # Check if we got non-zero data (beyond the report ID)
                if any(b != 0 for b in data[1:]):
                    found.append(report_id)
                    hex_str = " ".join(f"{b:02X}" for b in data[:min(32, len(data))])
                    if len(data) > 32:
                        hex_str += " ..."
                    print(f"  Report ID 0x{report_id:02X}: {hex_str}")
            except IOError:
                pass

        if not found:
            print("  No valid feature reports found on this interface.")
        else:
            print(f"\n  Found {len(found)} valid report ID(s): "
                  f"{', '.join(f'0x{r:02X}' for r in found)}")

        dev.close()


def cmd_dump(report_id):
    """Dump a specific feature report from the config interface."""
    dev = MX3100Device()
    try:
        dev.open()
    except IOError as e:
        print(f"ERROR: {e}")
        return

    print(f"Device opened (Feature Report Size: {dev.feature_report_len} bytes)")
    print(f"Reading report ID 0x{report_id:02X}...\n")

    try:
        data = dev.get_feature(report_id, dev.feature_report_len)
        # Format as hex dump
        for offset in range(0, len(data), 16):
            chunk = data[offset:offset+16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            print(f"  {offset:04X}: {hex_part:<48}  {ascii_part}")
    except IOError as e:
        print(f"  Failed: {e}")

    dev.close()


def cmd_send(report_id, hex_data):
    """Send a feature report with custom data."""
    data = [report_id] + [int(h, 16) for h in hex_data.split()]
    dev = MX3100Device()
    try:
        dev.open()
    except IOError as e:
        print(f"ERROR: {e}")
        return

    # Pad to feature report length
    while len(data) < dev.feature_report_len:
        data.append(0)

    hex_str = " ".join(f"{b:02X}" for b in data[:32])
    print(f"Sending: {hex_str} ...")

    try:
        dev.set_feature(data)
        print("OK - Feature report sent successfully")
    except IOError as e:
        print(f"Failed: {e}")

    dev.close()


def cmd_watch():
    """Continuously read feature reports to detect config changes."""
    dev = MX3100Device()
    try:
        dev.open()
    except IOError as e:
        print(f"ERROR: {e}")
        return

    print(f"Watching device (Feature Report Size: {dev.feature_report_len} bytes)")
    print("Use the original MX-3100 software to change settings while this runs.")
    print("Press Ctrl+C to stop.\n")

    # Read initial state of known report IDs
    prev_states = {}
    for rid in range(256):
        try:
            data = dev.get_feature(rid, dev.feature_report_len)
            if any(b != 0 for b in data[1:]):
                prev_states[rid] = data
        except IOError:
            pass

    print(f"Tracking {len(prev_states)} active report IDs: "
          f"{', '.join(f'0x{r:02X}' for r in sorted(prev_states))}")
    print("Waiting for changes...\n")

    try:
        while True:
            for rid in sorted(prev_states.keys()):
                try:
                    data = dev.get_feature(rid, dev.feature_report_len)
                    if data != prev_states[rid]:
                        old_data = prev_states[rid]
                        timestamp = time.strftime("%H:%M:%S")
                        print(f"[{timestamp}] Report 0x{rid:02X} CHANGED:")
                        for i in range(len(data)):
                            if i < len(old_data) and data[i] != old_data[i]:
                                print(f"  Byte {i:3d}: 0x{old_data[i]:02X} -> 0x{data[i]:02X}")
                        prev_states[rid] = data
                        print()
                except IOError:
                    pass
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopped.")

    dev.close()


def main():
    parser = argparse.ArgumentParser(
        description="MX-3100 HID Protocol Sniffer - Discover mouse configuration protocol"
    )
    parser.add_argument("--probe", action="store_true",
                        help="Probe all report IDs on all interfaces")
    parser.add_argument("--dump", type=lambda x: int(x, 0), metavar="REPORT_ID",
                        help="Dump a specific feature report (e.g. 0x07)")
    parser.add_argument("--send", nargs=2, metavar=("REPORT_ID", "HEX_DATA"),
                        help='Send a feature report: --send 0x07 "02 00 01"')
    parser.add_argument("--watch", action="store_true",
                        help="Watch for feature report changes in real-time")
    parser.add_argument("--interface", type=int, metavar="N",
                        help="Target specific interface index (for --probe)")

    args = parser.parse_args()

    if args.probe:
        cmd_probe(args.interface)
    elif args.dump is not None:
        cmd_dump(args.dump)
    elif args.send:
        rid = int(args.send[0], 0)
        cmd_send(rid, args.send[1])
    elif args.watch:
        cmd_watch()
    else:
        cmd_list()


if __name__ == "__main__":
    main()
