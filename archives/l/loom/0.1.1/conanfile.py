#!/usr/bin/env python3
"""Conan recipe for loom 0.1.1, a lock-less C99 thread pool."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get


class LoomConan(ConanFile):
    name = "loom"
    version = "0.1.1"
    description = "A lock-less thread pool for C99"
    license = "ISC"
    homepage = "https://github.com/silentbicycle/loom"
    url = "https://github.com/silentbicycle/loom"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def configure(self):
        self.settings.rm_safe("os.version")

    def validate(self):
        if self.options.shared:
            raise ConanInvalidConfiguration("loom 0.1.1 only supports static builds")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # The upstream project has no configure/CMake system. Its Makefile
        # builds the static library and the complete upstream test/benchmark
        # suite; keep that entry point so the package build is test-backed.
        self.run("make clean", cwd=self.source_folder)
        self.run("make CC=clang ci", cwd=self.source_folder)

    def package(self):
        copy(self, "loom.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libloom.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "loom")
        self.cpp_info.set_property("cmake_target_name", "loom::loom")
        self.cpp_info.libs = ["loom"]
        self.cpp_info.system_libs = ["pthread"]
