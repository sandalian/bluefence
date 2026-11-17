#!/usr/bin/env python3
"""BlueFence 0.3 - cross-platform Bluetooth proximity monitor.

Watches for a Bluetooth (BLE) device and runs a command when it leaves or
returns to range, e.g. lock the screen when your phone walks away.

Requires: pip install bleak
Works on: Windows 10+, Linux (BlueZ), macOS 10.15+

Notes
- Windows/Linux identify devices by MAC address (AA:BB:CC:DD:EE:FF).
- macOS hides MAC addresses and exposes a per-host UUID instead; run
  `bluefence3.py --list` and use the address or name shown there.
"""

import argparse
import asyncio
import os
import platform
import subprocess
import sys
import time

# Default command to run when the device goes out of range (screen lock).
# These lock the local session; override with -g to do anything else.
DEFAULT_GONE_COMMANDS = {
    "Windows": "rundll32.exe user32.dll,LockWorkStation",
    "Darwin": "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession -suspend",
    "Linux": "loginctl lock-session",
}

DEFAULT_BACK_COMMANDS = {
    # Nothing to do by default; -b 'command' if you want e.g. brightness restore.
    "Windows": None,
    "Darwin": None,
    "Linux": None,
}


def default_command(mapping, os_name):
    if os_name in mapping:
        return mapping[os_name]
    return None


def run_command(command, reason, dry_run=False):
    """Run a shell command for a proximity event. Failures are reported, not fatal."""
    if not command:
        return
    if dry_run:
        print(f"[dry-run] {reason}: {command}")
        return
    try:
        proc = subprocess.run(command, shell=True)
        if proc.returncode != 0:
            print(f"ER: command for '{reason}' exited with {proc.returncode}: {command}")
    except OSError as exc:
        print(f"ER: could not run command for '{reason}': {exc}")


def import_bleak():
    try:
        from bleak import BleakScanner
    except ImportError:
        print("ER: the 'bleak' package is required. Install it with:\n    pip install bleak")
        sys.exit(1)
    return BleakScanner


async def list_devices(scan_timeout):
    BleakScanner = import_bleak()
    print(f"Scanning for {scan_timeout:.0f}s...")
    devices = await BleakScanner.discover(timeout=scan_timeout)
    if not devices:
        print("No Bluetooth devices found (is Bluetooth on and the device discoverable?).")
        return
    print(f"{'Address':<40} Name")
    for device in sorted(devices, key=lambda d: (d.name or "", d.address)):
        print(f"{device.address:<40} {device.name or '-'}")


async def find_device(target, scan_timeout):
    """Return the target device if it advertises within scan_timeout, else None.

    Matches the address/UUID first, then the advertised name. Name matching is
    the reliable path on macOS, where addresses are host-specific UUIDs.
    """
    BleakScanner = import_bleak()
    wanted = target.lower()

    def matches(device, advertisement_data):
        address = (device.address or "").lower()
        name = (device.name or "").lower()
        return address == wanted or (name and name == wanted)

    return await BleakScanner.find_device_by_filter(matches, timeout=scan_timeout)


async def monitor(args):
    os_name = platform.system()
    gone_cmd = args.gone if args.gone is not None else default_command(DEFAULT_GONE_COMMANDS, os_name)
    back_cmd = args.back if args.back is not None else default_command(DEFAULT_BACK_COMMANDS, os_name)

    if not args.verbose:
        print(f"Watching {args.device} every ~{args.interval:.0f}s "
              f"(lock after {args.max_missed + 1} missed scans)")

    # Probe once so a typo/disabled adapter fails fast instead of locking later.
    try:
        device = await find_device(args.device, args.scan_timeout)
    except Exception as exc:  # bleak raises platform-specific errors here
        print(f"ER: Bluetooth scan failed: {exc}")
        return 2

    if device is None:
        print(f"ER: '{args.device}' was not seen. Run --list to find its address/name.")
        return 2

    print(f"OK: Found {device.name or device.address} ({device.address})")
    in_range = True
    missed = 0

    while True:
        try:
            device = await find_device(args.device, args.scan_timeout)
        except Exception as exc:
            print(f"ER: Bluetooth scan failed: {exc}")
            await asyncio.sleep(args.interval)
            continue

        now = time.strftime("%H:%M:%S")

        if device is not None:
            if not in_range:
                run_command(back_cmd, "device back in range", args.dry_run)
                in_range = True
            missed = 0
            status = "near"
        else:
            missed += 1
            if in_range and missed > args.max_missed:
                run_command(gone_cmd, "device out of range", args.dry_run)
                in_range = False
            status = "away" if in_range else "GONE!"

        print(f"{status} | missed {missed} | in range {in_range} | {now}")

        await asyncio.sleep(args.interval)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="BlueFence - run a command when a Bluetooth device leaves/returns to range.",
        epilog="Examples:\n"
               "  bluefence3.py --list\n"
               "  bluefence3.py AA:BB:CC:DD:EE:FF\n"
               "  bluefence3.py AA:BB:CC:DD:EE:FF -g 'loginctl lock-session' -b 'echo welcome back'\n"
               "  bluefence3.py My-Phone --dry-run",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("device", nargs="?",
                        help="Device MAC address on Windows/Linux, or address/UUID/name on macOS")
    parser.add_argument("-g", "--gone",
                        help="Command to run when the device goes out of range "
                             "(default: lock the screen for this OS)")
    parser.add_argument("-b", "--back",
                        help="Command to run when the device comes back in range (default: none)")
    parser.add_argument("-i", "--interval", type=float, default=5.0,
                        help="Seconds to wait between scans (default: 5)")
    parser.add_argument("-t", "--scan-timeout", type=float, default=None,
                        help="Seconds per scan before counting a miss (default: interval - 1)")
    parser.add_argument("-m", "--max-missed", type=int, default=3,
                        help="Consecutive misses before the device counts as gone (default: 3)")
    parser.add_argument("--list", action="store_true",
                        help="List nearby Bluetooth devices and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print commands instead of running them")
    parser.add_argument("-q", "--quiet", dest="verbose", action="store_false",
                        help="Only print status lines")
    args = parser.parse_args(argv)

    if args.scan_timeout is None:
        args.scan_timeout = max(args.interval - 1.0, 1.0)
    if args.list:
        return args
    if not args.device:
        parser.error("a device address/name is required (or use --list)")
    if args.interval < 1 or args.scan_timeout < 1:
        parser.error("interval and scan timeout must be at least 1 second")
    if args.max_missed < 0:
        parser.error("max-missed cannot be negative")
    return args


def main(argv=None):
    args = parse_args(argv)

    # The default proactor loop cannot run bleak's WinRT scanner.
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        if args.list:
            asyncio.run(list_devices(args.scan_timeout))
            return 0
        return asyncio.run(monitor(args)) or 0
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
