#!/usr/bin/env python3
"""Conan recipe for libforensic1394 0.2 on HarmonyOS (OHOS).

libforensic1394 drives the local IEEE 1394 ("FireWire") controller through the
Linux "Juju" userspace ABI: linux/firewire-cdev.h plus the /dev/fw* char
devices and the /sys/bus/firewire attribute files.  The OHOS SDK sysroot ships
that header (and linux/firewire-constants.h) in full, so the backend compiles
unmodified.  Upstream 0.2 selects it with

    IF("${CMAKE_SYSTEM}" MATCHES "Linux")

and CMake reports CMAKE_SYSTEM_NAME=HarmonyOS on this platform, so
patches/0001 widens the condition to also match HarmonyOS instead of letting
the build fall through to the unsupported-platform branch.

CMake 4 removed compatibility with the upstream `CMAKE_MINIMUM_REQUIRED
(VERSION 2.8)`, so build() passes CMAKE_POLICY_VERSION_MINIMUM=3.5 on the
configure command line rather than rewriting the upstream build files.  A
toolchain-file cache entry is not enough here: the project's first command is
CMAKE_MINIMUM_REQUIRED, which cmake executes before the toolchain file is
loaded.

The 0.2 release contains no test suite of its own (the published tarball and
the upstream master branch both ship no tests directory), so verification is
the installed-package consumer test in test_package/ - see notes.md for the
upstream inventory evidence.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class Libforensic1394Conan(ConanFile):
    name = "libforensic1394"
    version = "0.2"
    description = (
        "Library for performing live memory forensics over the IEEE 1394 "
        "(FireWire) interface using the Linux/Juju firewire-cdev ABI"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://freddie.witherden.org/tools/libforensic1394/"
    url = "https://freddie.witherden.org/tools/libforensic1394/"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} requires the Linux/Juju firewire-cdev ABI, "
                f"which {self.settings.os} does not provide"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream builds both libraries by default; the Conan option decides.
        tc.variables["FORENSIC1394_BUILD_SHARED"] = (
            "ON" if self.options.shared else "OFF"
        )
        tc.variables["FORENSIC1394_BUILD_STATIC"] = (
            "ON" if not self.options.shared else "OFF"
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMake 4 dropped compatibility with the upstream
        # cmake_minimum_required(VERSION 2.8).  The policy floor has to be a
        # configure-time command line definition: CMakeLists.txt consumes it in
        # its very first command, which runs before the toolchain file's cache
        # entries are in scope.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        for license_file in ("COPYING", "COPYING.LESSER"):
            copy(
                self,
                license_file,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.libs = ["forensic1394"]
