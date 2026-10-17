#!/usr/bin/env python3
"""Conan recipe for alpine-chroot-install 0.14.0 — pure POSIX shell script.

alpine-chroot-install installs an Alpine Linux system into a chroot.
It is a single POSIX shell script (no compilation step); the upstream
Makefile only has an `install` target that copies the script to
$(PREFIX)/bin. OHOS hosts lack the coreutils `install` binary, so the
package step performs the copy + chmod directly.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AlpineChrootInstallConan(ConanFile):
    name = "alpine-chroot-install"
    version = "0.14.0"
    description = "Install Alpine Linux in a chroot"
    license = "MIT"
    homepage = "https://github.com/alpinelinux/alpine-chroot-install"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure shell script — no compilation step
        pass

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "alpine-chroot-install", src=self.source_folder,
             dst=bindir, keep_path=False)
        os.chmod(os.path.join(bindir, "alpine-chroot-install"), 0o755)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Pure script project: executables in bin/, no libraries
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
