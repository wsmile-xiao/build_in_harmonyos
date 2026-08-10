#!/usr/bin/env python3
"""Conan recipe for alpine-make-rootfs 0.8.1."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AlpineMakeRootfsConan(ConanFile):
    name = "alpine-make-rootfs"
    version = "0.8.1"
    description = "Create Alpine Linux root filesystem images for containers"
    license = "MIT"
    homepage = "https://github.com/alpinelinux/alpine-make-rootfs"
    url = ""
    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "alpine-make-rootfs", src=self.source_folder, dst=bindir, keep_path=False)
        os.chmod(os.path.join(bindir, "alpine-make-rootfs"), 0o755)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
