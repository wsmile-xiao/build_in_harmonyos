#!/usr/bin/env python3
"""Conan recipe for serialdv 1.1.5 — C++ interface to encode/decode audio with
AMBE3000 based devices (DVSI ThumbDV and compatibles) in packet mode over a
serial link or an AMBE-over-UDP server.

OHOS adaptation notes:
  * Upstream is a plain CMake project with no third-party dependencies.  The
    OHOS SDK sysroot provides every header/API the sources use:
    linux/serial.h (struct serial_struct), TIOCGSERIAL/TIOCSSERIAL via
    sys/ioctl.h (<aarch64-linux-ohos/bits/ioctl.h>), ASYNC_LOW_LATENCY via
    linux/tty_flags.h and B230400/B460800 in bits/termios.h, so the build is
    patch-free.
  * The library is built SHARED exactly as upstream CMakeLists declares
    (add_library(serialdv SHARED ...)).  serialdv is not a system-name
    library, so Conan keeps control of the runtime dependency chain (R26).
  * BUILD_TOOL mirrors the upstream option (default ON): the dvtest utility
    is installed to bin/ and is declared in the software-level commands.json
    (R38).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os

required_conan_version = ">=2.0"


class SerialDvConan(ConanFile):
    name = "serialdv"
    version = "1.1.5"
    description = ("C++ interface to encode/decode audio with AMBE3000 based "
                   "devices in packet mode")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/f4exb/serialDV"
    url = "https://github.com/f4exb/serialDV"
    topics = ("ambe", "ambe3000", "dv", "d-star", "dmr", "serial", "ham-radio")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"BUILD_TOOL": [True, False]}
    default_options = {"BUILD_TOOL": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "serialdv targets POSIX systems only (serial termios / UDP "
                "sockets); supported: Linux, OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TOOL"] = "ON" if self.options.BUILD_TOOL else "OFF"
        # CMake's Platform/OHOS module (include(Platform/Linux)) has no SONAME
        # support, so the upstream VERSION/SOVERSION properties do not emit an
        # ELF DT_SONAME and CI's L5a gate fails.  Emit the installed file name
        # explicitly, matching the repo convention for OHOS CMake ports
        # (apache-arrow patches/0002, boost patches/0001).
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,-soname,libserialdv.so"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["serialdv"]
        self.cpp_info.set_property("cmake_file_name", "serialdv")
        self.cpp_info.set_property("cmake_target_name", "serialdv::serialdv")
