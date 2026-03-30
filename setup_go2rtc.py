#!/usr/bin/env python3
"""Download the go2rtc binary for the current platform."""

import os
import platform
import stat
import sys
import urllib.request
import zipfile
import tempfile

REPO = "AlexxIT/go2rtc"
VERSION = "v1.9.9"
BASE_URL = f"https://github.com/{REPO}/releases/download/{VERSION}"

PLATFORM_MAP = {
    ("Linux", "x86_64"): "go2rtc_linux_amd64",
    ("Linux", "aarch64"): "go2rtc_linux_arm64",
    ("Linux", "armv7l"): "go2rtc_linux_arm",
    ("Darwin", "x86_64"): "go2rtc_mac_amd64.zip",
    ("Darwin", "arm64"): "go2rtc_mac_arm64.zip",
    ("Windows", "AMD64"): "go2rtc_win64.zip",
    ("Windows", "x86"): "go2rtc_win32.zip",
}

BIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")


def detect_platform():
    system = platform.system()
    machine = platform.machine()
    key = (system, machine)
    if key not in PLATFORM_MAP:
        print(f"Unsupported platform: {system} {machine}")
        print(f"Supported: {', '.join(f'{s} {m}' for s, m in PLATFORM_MAP)}")
        sys.exit(1)
    return PLATFORM_MAP[key]


def download(filename):
    url = f"{BASE_URL}/{filename}"
    print(f"Downloading {url} ...")

    os.makedirs(BIN_DIR, exist_ok=True)

    is_windows = platform.system() == "Windows"
    binary_name = "go2rtc.exe" if is_windows else "go2rtc"
    dest = os.path.join(BIN_DIR, binary_name)

    if filename.endswith(".zip"):
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            urllib.request.urlretrieve(url, tmp.name)
            with zipfile.ZipFile(tmp.name, "r") as zf:
                # Find the binary inside the zip
                for name in zf.namelist():
                    if "go2rtc" in name.lower():
                        with zf.open(name) as src, open(dest, "wb") as dst:
                            dst.write(src.read())
                        break
            os.unlink(tmp.name)
    else:
        urllib.request.urlretrieve(url, dest)

    if not is_windows:
        st = os.stat(dest)
        os.chmod(dest, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    print(f"Installed: {dest}")
    return dest


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Download go2rtc binary")
    parser.add_argument("--force", action="store_true", help="Re-download even if binary exists")
    args = parser.parse_args()

    is_windows = platform.system() == "Windows"
    binary_name = "go2rtc.exe" if is_windows else "go2rtc"
    dest = os.path.join(BIN_DIR, binary_name)

    if os.path.exists(dest) and not args.force:
        print(f"go2rtc already exists at {dest}")
        print("Use --force to re-download.")
        return

    filename = detect_platform()
    download(filename)
    print("Done! You can now run: python run.py")


if __name__ == "__main__":
    main()
