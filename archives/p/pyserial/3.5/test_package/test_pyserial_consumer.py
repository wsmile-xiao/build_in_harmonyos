#!/usr/bin/env python3
"""Real consumer test for pyserial's packaged loopback API."""

import os
import sys


def main():
    if len(sys.argv) != 2:
        raise AssertionError(f"usage: {sys.argv[0]} <package-folder>")
    package_folder = os.path.abspath(sys.argv[1])
    site_packages = os.path.join(package_folder, "lib", "python", "site-packages")
    serial_package = os.path.join(site_packages, "serial")
    if not os.path.isdir(serial_package):
        raise AssertionError(f"Conan package serial module missing: {serial_package}")
    sys.path.insert(0, site_packages)

    import serial

    imported_from = os.path.abspath(serial.__file__)
    if not imported_from.startswith(os.path.abspath(serial_package) + os.sep):
        raise AssertionError(f"serial imported outside Conan package: {imported_from}")
    assert serial.VERSION == "3.5", serial.VERSION
    with serial.serial_for_url("loop://", timeout=1) as port:
        payload = b"pyserial consumer test"
        assert port.write(payload) == len(payload)
        assert port.read(len(payload)) == payload
    assert serial.serial_for_url("loop://", do_not_open=True).portstr == "loop://"
    print("OK: pyserial package path, VERSION, loopback write/read, and URL API")


if __name__ == "__main__":
    main()
