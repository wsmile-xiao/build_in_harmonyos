#!/usr/bin/env python3
"""Conan recipe for acpitool 0.5.1.

acpitool - ACPI event gathering command-line tool.
Build system: Autotools (configure + make).
C++ project, no third-party Conan dependencies (only musl libc).
Runtime limitation: HarmonyOS PC lacks /proc/acpi & /sys/bus/acpi.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AcpitoolConan(ConanFile):
    name = "acpitool"
    version = "0.5.1"
    description = "acpitool - ACPI event gathering command-line tool"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/acpitool/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # TMPDIR must be set for config.status temp file creation on HarmonyOS.
        # Use self.build_folder/conftmp which is created in build() below.
        import os
        tmpdir = os.path.join(self.build_folder, "conftmp")
        tc.extra_env = {"TMPDIR": tmpdir}
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Pre-create temp dir and patch configure to use it, bypassing
        # the mktemp -d permission issue on HarmonyOS.
        import os
        tmpdir = os.path.join(self.build_folder, "conftmp")
        os.makedirs(tmpdir, exist_ok=True)
        self.run("sed -i 's|mktemp -d \"./confXXXXXX\"|echo " + tmpdir + "|' configure", cwd=self.source_folder)
        self.run("sed -i 's|tmp=./conf\\$\\$-$RANDOM|tmp=" + tmpdir + "|' configure", cwd=self.source_folder)
        self.run("sed -i 's|(umask 077 && mkdir \"$tmp\")|:|' configure", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]