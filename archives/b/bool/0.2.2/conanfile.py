#!/usr/bin/env python3
"""Conan recipe for GNU Bool 0.2.2."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BoolConan(ConanFile):
    name = "bool"
    version = "0.2.2"
    description = "GNU utility for finding files that match a boolean expression"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/bool/"
    url = ""
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} supports only Linux and OHOS, not {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # The release tarball contains generated Autotools files and builds
        # in the source tree; keep the helper in the same directory.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The patched config.guess detects the native OHOS host. Do not let a
        # profile inject build/host overrides that would force cross mode.
        tc.configure_args = [
            arg
            for arg in tc.configure_args
            if not str(arg).startswith("--build=")
            and not str(arg).startswith("--host=")
        ]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # E011: Autoconf-generated config.status uses umask 077 for its
        # temporary awk files; HMDFS makes that directory non-writable.
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            replace_in_file(self, configure, "umask 077", "umask 022", strict=False)

        # HMDFS may strip executable bits from files extracted from a
        # tarball; Autotools must be able to invoke all helper scripts.
        for relative in (
            "configure",
            "config.guess",
            "config.sub",
            "install-sh",
            "missing",
        ):
            path = os.path.join(self.source_folder, "build-aux", relative)
            if relative == "configure":
                path = os.path.join(self.source_folder, relative)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | 0o111)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Keep the complete upstream shell suite in the Conan build log.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        # OHOS does not provide the coreutils install command on the device.
        # Copy the exact files named by the upstream install targets instead.
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "bool", src=os.path.join(self.source_folder, "src"), dst=bin_dir)
        copy(
            self,
            "bool.1",
            src=os.path.join(self.source_folder, "doc"),
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        binary = os.path.join(bin_dir, "bool")
        if os.path.isfile(binary):
            os.chmod(binary, os.stat(binary).st_mode | 0o111)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
