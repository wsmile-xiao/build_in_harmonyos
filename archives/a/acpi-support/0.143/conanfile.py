#!/usr/bin/env python3
"""Conan recipe — acpi-support 0.143 (zero-compile script/config package)

acpi-support is the laptop ACPI event "glue": acpid event configs, shell
handler scripts, and a wireless-state shell function library. Upstream
ships no build system and no compiled artifacts — the recipe therefore
performs bash syntax validation as the build step and installs the files
in the Debian layout (/etc/acpi, /etc/acpi/events, /usr/share/acpi-support).

Platform task: 开源鸿蒙PC专项积分赛 · acpi-support 0.143.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AcpiSupportConan(ConanFile):
    name = "acpi-support"
    version = "0.143"
    description = "Laptop ACPI event glue scripts (acpid event configs, shell handlers, wireless state functions)"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/acpi-support"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["0.143"], strip_root=True)

    def _bash(self):
        # R5: OHOS workers have no /bin/sh; CONFIG_SHELL is injected by CI,
        # local runs fall back to PATH, then the known HNP location.
        return (os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash")

    def build(self):
        # Zero-compile package: the build step validates every shell script
        # (bash -n) and sanity-checks the main config, so a corrupted or
        # truncated source cannot reach package().
        src = self.source_folder
        bash = self._bash()
        scripts = [
            "asus-keyboard-backlight.sh",
            "asus-wireless.sh",
            "ibm-wireless.sh",
            "tosh-wireless.sh",
            "undock.sh",
            "lib/state-funcs",
        ]
        for s in scripts:
            self.run('"{}" -n "{}"'.format(bash, os.path.join(src, s)))
        # Sanity: main config declares the suspend/hibernate method section.
        self.run('"{}" -c \'grep -q "Suspend/hibernate method" "{}"\''.format(
            bash, os.path.join(src, "acpi-support")))
        # Sanity: every event file defines an action= line.
        for ev in os.listdir(os.path.join(src, "events")):
            self.run('"{}" -c \'grep -q "^action=" "{}"\''.format(
                bash, os.path.join(src, "events", ev)))

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        # Shell handlers → /etc/acpi (Debian rules chmod a+x every *.sh)
        for f in ("asus-keyboard-backlight.sh", "asus-wireless.sh",
                  "ibm-wireless.sh", "tosh-wireless.sh", "undock.sh"):
            copy(self, f, src, os.path.join(pkg, "etc", "acpi"))
        # Main config → /etc/acpi/acpi-support (0644, Debian ships it non-exec)
        copy(self, "acpi-support", src, os.path.join(pkg, "etc", "acpi"))
        # Event configs → /etc/acpi/events
        copy(self, "*", os.path.join(src, "events"),
             os.path.join(pkg, "etc", "acpi", "events"))
        # Support files → /usr/share/acpi-support (0644, Debian chmod a-x)
        copy(self, "key-constants", src,
             os.path.join(pkg, "usr", "share", "acpi-support"))
        copy(self, "state-funcs", os.path.join(src, "lib"),
             os.path.join(pkg, "usr", "share", "acpi-support"))
        # License
        copy(self, "COPYING", src, os.path.join(pkg, "licenses"))
        # Exec bits: handlers executable, config/state-funcs non-executable
        for f in ("asus-keyboard-backlight.sh", "asus-wireless.sh",
                  "ibm-wireless.sh", "tosh-wireless.sh", "undock.sh"):
            os.chmod(os.path.join(pkg, "etc", "acpi", f), 0o755)
        for f in ("acpi-support",):
            os.chmod(os.path.join(pkg, "etc", "acpi", f), 0o644)
        for f in ("key-constants", "state-funcs"):
            os.chmod(os.path.join(pkg, "usr", "share", "acpi-support", f), 0o644)

    def package_info(self):
        # Pure script/config application: nothing to link or include.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.env_info.ACPI_SUPPORT_DIR = os.path.join(self.package_folder, "etc", "acpi")
