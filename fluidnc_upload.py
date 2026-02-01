#!/usr/bin/env python3
"""Upload G-code files to a FluidNC controller via its REST API.

FluidNC is an ESP32-based CNC/laser controller. This tool uploads files
to its SD card (or flash filesystem) over the network.

Usage:
    fluidnc-upload panel.gcode
    fluidnc-upload panel.gcode --host 192.168.1.100
    fluidnc-upload *.gcode --host laser
"""

import argparse
import os
import sys

import requests


def upload_file(filename, host, port=80, use_sd=True):
    """Upload a file to FluidNC via REST API."""
    if not os.path.exists(filename):
        print(f"Error: file not found: {filename}", file=sys.stderr)
        return False

    url = f"http://{host}:{port}/files"
    target_filename = os.path.basename(filename)

    if use_sd:
        target_filename = f"/sd/{target_filename}"
        dest = "SD card"
    else:
        dest = "Flash"

    try:
        # Check if file already exists and delete it
        list_url = f"http://{host}:{port}/files"
        if use_sd:
            list_url += "?path=/sd/"
        response = requests.get(list_url, timeout=10)
        if response.status_code == 200:
            files_data = response.json()
            files_list = files_data.get("files", [])
            if any(f["name"] == os.path.basename(filename) for f in files_list):
                print(f"  Replacing existing file on {dest}")
                delete_url = f"http://{host}:{port}/files?name={target_filename}&action=delete"
                requests.get(delete_url, timeout=10)

        # Upload
        print(f"  Uploading {filename} to {dest}...")
        with open(filename, "rb") as f:
            files = {"file": (target_filename, f)}
            response = requests.post(url, files=files, timeout=60)

        if response.status_code == 200:
            print(f"  OK")
            return True
        else:
            print(f"  Upload failed (HTTP {response.status_code}): {response.text}", file=sys.stderr)
            return False

    except requests.exceptions.ConnectionError:
        print(f"Error: cannot connect to FluidNC at {host}:{port}", file=sys.stderr)
        return False
    except requests.exceptions.Timeout:
        print(f"Error: connection timed out to {host}:{port}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Upload G-code files to a FluidNC controller",
        epilog="Example: fluidnc-upload panel.gcode --host 192.168.1.100",
    )
    parser.add_argument("files", nargs="+", help="G-code files to upload")
    parser.add_argument("--host", default="localhost", help="FluidNC hostname or IP (default: localhost)")
    parser.add_argument("--port", type=int, default=80, help="FluidNC port (default: 80)")
    parser.add_argument(
        "--flash",
        action="store_true",
        help="Upload to Flash filesystem instead of SD card",
    )

    args = parser.parse_args()

    success = True
    for filename in args.files:
        if not upload_file(filename, args.host, args.port, use_sd=not args.flash):
            success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
