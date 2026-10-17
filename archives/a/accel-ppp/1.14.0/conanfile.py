#!/usr/bin/env python3
"""Conan recipe for accel-ppp 1.14.0 — Linux PPP/PPPoE/L2TP/SSTP server.

CMake-based daemon. Requires OpenSSL, PCRE2 and libucontext (OHOS musl libc
lacks getcontext/setcontext; see the libucontext package).
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AccelPppConan(ConanFile):
    name = "accel-ppp"
    version = "1.14.0"
    description = "High-performance PPTP/PPPoE/L2TP/SSTP server"
    license = "GPL-2.0-or-later"
    homepage = "https://accel-ppp.io/"
    url = "https://github.com/accel-ppp/accel-ppp"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1.1")
        self.requires("pcre2/10.45.1.1")
        # OHOS musl libc has no getcontext/setcontext; ucontext comes from this package.
        self.requires("libucontext/1.5.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # Kernel driver modules cannot be built in the OHOS application SDK;
        # keep them off.  RADIUS and SHAPER are pure userspace modules (only
        # need OpenSSL / Linux headers) and are enabled so the full upstream
        # module set is available at runtime.
        tc.variables["BUILD_PPTP_DRIVER"] = "OFF"
        tc.variables["BUILD_IPOE_DRIVER"] = "OFF"
        tc.variables["BUILD_VLAN_MON_DRIVER"] = "OFF"
        tc.variables["LOG_PGSQL"] = "OFF"
        tc.variables["RADIUS"] = "ON"
        tc.variables["SHAPER"] = "ON"
        tc.variables["NETSNMP"] = "OFF"
        tc.variables["LUA"] = "OFF"
        # Upstream CMake uses find_library/find_path for pcre2/openssl and a
        # bare `ucontext` link; feed the dependency include/lib dirs so the
        # Conan-provided packages are located.
        include_dirs = []
        lib_dirs = []
        for dep in ("openssl", "pcre2", "libucontext"):
            cpp = self.dependencies[dep].cpp_info
            include_dirs += cpp.includedirs
            lib_dirs += cpp.libdirs
        tc.variables["CMAKE_INCLUDE_PATH"] = ";".join(include_dirs)
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = " ".join(f"-L{d}" for d in lib_dirs)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream installs accel-pppd to sbin/ and accel-cmd to bin/. Conan
        # convention (and the CI negative test, which removes bin/ and lib/)
        # expects executables under bin/, so fold sbin/ into bin/.
        sbin = os.path.join(self.package_folder, "sbin")
        if os.path.isdir(sbin):
            os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
            for name in os.listdir(sbin):
                shutil.move(
                    os.path.join(sbin, name),
                    os.path.join(self.package_folder, "bin", name),
                )
            os.rmdir(sbin)

    def package_info(self):
        # accel-pppd + accel-cmd under bin/; module .so files in lib/accel-ppp.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
