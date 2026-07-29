#!/usr/bin/env python3
"""Offline compatibility checks for hwdata's host-tool-dependent tests."""

import re
import sys
from pathlib import Path


ID4 = re.compile(r"^[0-9a-fA-F]{4}$")
PCI_DUMP_HEADER = re.compile(
    r"^[0-9a-fA-F:.]+\s+[0-9a-fA-F]{4}:\s+"
    r"([0-9a-fA-F]{4}):([0-9a-fA-F]{4})(?:\s|$)"
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_id_database(path):
    vendors = {}
    products = {}
    current_vendor = None
    previous_vendor = None
    previous_product = None

    for lineno, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if (
            len(raw_line) >= 6
            and not raw_line.startswith("\t")
            and ID4.fullmatch(raw_line[:4])
            and raw_line[4].isspace()
        ):
            vendor = raw_line[:4].lower()
            require(
                previous_vendor is None or vendor > previous_vendor,
                f"{path}:{lineno}: vendor IDs are not strictly ordered",
            )
            vendors[vendor] = raw_line[5:].strip()
            products[vendor] = set()
            current_vendor = vendor
            previous_vendor = vendor
            previous_product = None
        elif (
            len(raw_line) >= 7
            and raw_line.startswith("\t")
            and ID4.fullmatch(raw_line[1:5])
            and raw_line[5].isspace()
            and current_vendor is not None
        ):
            product = raw_line[1:5].lower()
            require(
                previous_product is None or product > previous_product,
                f"{path}:{lineno}: product IDs are not strictly ordered",
            )
            products[current_vendor].add(product)
            previous_product = product

    require(vendors, f"{path}: no vendor records")
    return vendors, products


def check_pci(pci_ids, dump):
    vendors, products = read_id_database(pci_ids)
    records = []
    config_rows = 0
    for raw_line in dump.read_text(encoding="utf-8").splitlines():
        match = PCI_DUMP_HEADER.match(raw_line)
        if match:
            records.append((match.group(1).lower(), match.group(2).lower()))
        elif re.match(r"^[0-9a-fA-F]{2}:(?: [0-9a-fA-F]{2}){16}$", raw_line):
            config_rows += 1

    require(len(records) >= 20, f"{dump}: expected at least 20 PCI records")
    require(
        config_rows >= len(records),
        f"{dump}: missing configuration rows for PCI records",
    )
    for vendor, device in records:
        require(vendor in vendors, f"{dump}: unknown PCI vendor {vendor}")
        require(
            device in products[vendor],
            f"{dump}: unknown PCI device {vendor}:{device}",
        )
    print(
        "PASS: pciutils dump compatibility check resolved "
        f"{len(records)} PCI records"
    )


def check_usb(usb_ids):
    vendors, products = read_id_database(usb_ids)
    product_count = sum(len(items) for items in products.values())
    require(len(vendors) >= 3000, f"{usb_ids}: unexpectedly few USB vendors")
    require(product_count >= 20000, f"{usb_ids}: unexpectedly few USB products")
    require(
        "Linux Foundation" in vendors.get("1d6b", ""),
        f"{usb_ids}: Linux Foundation vendor is absent",
    )
    require(
        {"0002", "0003"}.issubset(products["1d6b"]),
        f"{usb_ids}: Linux root-hub products are absent",
    )
    print(
        "PASS: offline USB compatibility check parsed "
        f"{len(vendors)} vendors and {product_count} products"
    )


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--pci":
        check_pci(Path(sys.argv[2]), Path(sys.argv[3]))
        return
    if len(sys.argv) == 3 and sys.argv[1] == "--usb":
        check_usb(Path(sys.argv[2]))
        return
    raise SystemExit(
        "usage: check_hwdata.py --pci <pci.ids> <lspci-dump.txt> "
        "| --usb <usb.ids>"
    )


if __name__ == "__main__":
    main()
