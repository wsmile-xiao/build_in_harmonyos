#!/usr/bin/env python3
"""Conan recipe — ttylog 0.31 (CMake serial-port logging CLI)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class TtylogConan(ConanFile):
    name = "ttylog"
    version = "0.31"
    description = "Log data from a serial device to standard output"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/ttylog/"
    url = "https://git.code.sf.net/p/ttylog/code"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ttylog requires Linux or OHOS termios")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)],
            strip_root=True, filename="ttylog-0.31.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if self.settings.os == "OHOS":
            # No OHOS musl loader on x86 CI runners; static executable is also
            # directly runnable by qemu-aarch64 for the upstream CLI tests.
            tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-static"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "ttylog", self.build_folder,
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "ttylog.8", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man8"),
             keep_path=False)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
