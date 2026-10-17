#!/usr/bin/env python3
"""Conan recipe — sloci-image 0.1.1

sloci-image is a POSIX sh script that creates single-layer OCI container images
from a rootfs directory or tarball. No compilation required — pure shell script.

Build system: plain Makefile (install target only, no configure).
License: MIT
Homepage: https://github.com/jirutka/sloci-image
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SlociImageConan(ConanFile):
    name = "sloci-image"
    version = "0.1.1"
    description = "A simple POSIX sh script for creating single-layer OCI container images"
    license = "MIT"
    homepage = "https://github.com/jirutka/sloci-image"
    url = "https://github.com/jirutka/sloci-image"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # sloci-image is a pure shell script — no compilation needed.
        # The Makefile's install target handles everything.

    def package(self):
        # Install the sloci-image script to bin/
        copy(self, "sloci-image", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
