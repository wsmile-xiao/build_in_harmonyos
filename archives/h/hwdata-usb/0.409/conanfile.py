#!/usr/bin/env python3
"""Conan recipe for the USB identifier database from hwdata 0.409."""

import os
import re
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class HwdataUsbConan(ConanFile):
    name = "hwdata-usb"
    version = "0.409"
    description = "USB vendor and product identification database"
    license = "GPL-2.0-or-later OR XFree86-1.1"
    homepage = "https://github.com/vcrhonek/hwdata"
    url = "https://github.com/vcrhonek/hwdata"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "tests/check_hwdata.py"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="hwdata-0.409.tar.gz",
            strip_root=True,
        )

    @property
    def _compat_test(self):
        return os.path.join(
            self.export_sources_folder,
            "tests",
            "check_hwdata.py",
        )

    def _run_compat_test(self, mode, *files):
        quoted = " ".join(
            [shlex.quote(sys.executable), shlex.quote(self._compat_test), mode]
            + [shlex.quote(name) for name in files]
        )
        self.run(quoted, cwd=self.source_folder)

    @staticmethod
    def _supports_lspci_dump(lspci):
        if not lspci:
            return False
        result = subprocess.run(
            [lspci, "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        return re.search(r"(^|\s)-A(?:\s|,|$)", result.stdout) is not None

    def build(self):
        if can_run(self):
            self.run("./configure --disable-blacklist", cwd=self.source_folder)
            lspci = shutil.which("lspci")
            if self._supports_lspci_dump(lspci):
                self.run(
                    "lspci -A dump -O dump.name=lspci-dump.txt -i pci.ids "
                    "> /dev/null",
                    cwd=self.source_folder,
                )
            else:
                self.output.warning(
                    "lspci does not provide the pciutils dump backend; "
                    "running the offline dump-to-pci.ids compatibility check"
                )
                self._run_compat_test(
                    "--pci",
                    "pci.ids",
                    "lspci-dump.txt",
                )
            self.run("python3 ./check-pci-ids.py", cwd=self.source_folder)
            if shutil.which("podman"):
                self.run("bash ./check-usb-ids.sh", cwd=self.source_folder)
            else:
                self.output.warning(
                    "Podman is unavailable; running the deterministic offline "
                    "USB database compatibility check"
                )
                self._run_compat_test("--usb", "usb.ids")
            for data_file in (
                "pci.ids",
                "usb.ids",
                "oui.txt",
                "iab.txt",
                "pnp.ids",
            ):
                self.run(
                    f'iconv -f UTF-8 "{data_file}" > /dev/null',
                    cwd=self.source_folder,
                )
            self.run(
                "grep 'Date:' pci.ids | head -1 && "
                "grep 'Date:' usb.ids | head -1",
                cwd=self.source_folder,
            )
        else:
            self.output.info(
                "Cross build: hwdata's native make-check suite must run in "
                "the Linux validation stage; the packaged USB data remains "
                "architecture independent."
            )

    def package(self):
        copy(
            self,
            "usb.ids",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "hwdata"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        usb_ids = os.path.join(
            self.package_folder, "share", "hwdata", "usb.ids"
        )
        self.runenv_info.define_path("USB_IDS_FILE", usb_ids)
