#!/usr/bin/env python3
"""Conan recipe for canvenient 1.02 — CMake project (C).

CANvenient is a C99 abstraction layer over multiple CAN APIs (SocketCAN on
Linux/OHOS, Ixxat/Kvaser/PEAK/Softing on Windows).

OHOS adaptation notes (see patches/0001):
- bionic's <sys/socket.h> must precede <linux/can.h>; the kernel header
  <linux/socket.h> otherwise redefines struct sockaddr_storage.
- the upstream build links an external "socketcan" (libsocketcan) target that
  is not published to the ohpcd registry; a vendored copy
  (deps/libsocketcan, LGPL-2.1, linux-can/libsocketcan) is compiled into the
  target instead, providing the single used symbol can_set_bitrate().
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, copy
import os


class CanvenientConan(ConanFile):
    name = "canvenient"
    version = "1.02"
    description = "Abstraction layer for multiple CAN APIs (SocketCAN, Ixxat, Kvaser, PEAK, Softing)"
    license = "MIT"
    homepage = "https://canopenterm.de/canvenient"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # Upstream installs a versioned shared library (libCANvenient.so.1); the
    # SocketCAN driver is the only non-Windows back-end and needs no external
    # deps on OHOS.  Keep shared (R26: not a system-name library).
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external conan requirements: libsocketcan is vendored (see
        # patches/0001) because the ohpcd registry does not publish it.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        from conan.tools.files import get
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["CANvenient"]
        self.cpp_info.set_property("cmake_file_name", "CANvenient")
        self.cpp_info.set_property("cmake_target_name", "CANvenient::CANvenient")
        self.cpp_info.set_property("pkg_config_name", "canvenient")
