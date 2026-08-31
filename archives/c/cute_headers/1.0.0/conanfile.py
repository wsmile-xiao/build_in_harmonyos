#!/usr/bin/env python3
"""Conan recipe — cute_headers 1.0.0 (header-only/custom)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class CuteHeadersConan(ConanFile):
    name = "cute_headers"
    version = "1.0.0"
    description = "Single-file cross-platform C and C++ libraries"
    license = "Zlib OR Unlicense"
    homepage = "https://github.com/RandyGaul/cute_headers"
    url = "https://github.com/RandyGaul/cute_headers"
    topics = ("header-only", "game-development", "c", "cpp")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "cute_*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "cute_headers")
        self.cpp_info.set_property(
            "cmake_target_name", "cute_headers::cute_headers"
        )

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cute_headers supports only Linux/OHOS"
            )

    def package_id(self):
        self.info.clear()