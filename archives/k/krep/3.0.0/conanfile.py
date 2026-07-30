#!/usr/bin/env python3
"""Conan recipe — krep 3.0.0

krep is a high-performance text search CLI implemented in C with a plain
Makefile build system.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class KrepConan(ConanFile):
    name = "krep"
    version = "3.0.0"
    description = "High-performance text search utility"
    license = "BSD-3-Clause"
    homepage = "https://github.com/davidesantangelo/krep"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        supported_os = ["Linux", "OHOS"]
        if self.settings.os not in supported_os:
            raise ConanInvalidConfiguration(f"{self.name} only supports {supported_os}")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cflags = "-Wall -Wextra -std=c11 -pthread -D_GNU_SOURCE -D_DEFAULT_SOURCE -fPIC"
        ldflags = "-pthread"
        if self.settings.build_type == "Debug":
            cflags += " -g -O0"
        else:
            cflags += " -O3"
        self.run(
            f"make CC=clang CFLAGS='{cflags}' LDFLAGS='{ldflags}'",
            cwd=self.source_folder,
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "krep", src=self.source_folder, dst=bindir)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
