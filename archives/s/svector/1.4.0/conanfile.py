#!/usr/bin/env python3
"""Conan recipe — svector 1.4.0

Compact SVO-optimized vector for C++17 or higher (upstream martinus/svector).
Header-only: the package installs include/ankerl/svector.h. Upstream drives
its own tests with meson while CMake only installs, so the recipe has no
compile step; the consumer test in test_package/ compiles against the
installed header and asserts real behavior (R34).
License: MIT (upstream LICENSE).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SvectorConan(ConanFile):
    name = "svector"
    version = "1.4.0"
    description = "Compact SVO optimized vector for C++17 or higher"
    license = "MIT"
    homepage = "https://github.com/martinus/svector"
    url = "https://github.com/martinus/svector"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only: nothing to compile; keep the patch-apply call for G1
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        # header-only: no build dependency on os/compiler/build_type
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
