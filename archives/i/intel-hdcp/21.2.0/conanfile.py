#!/usr/bin/env python3
"""Conan recipe for intel-hdcp 21.2.0 — Intel Unified HDCP SDK.

Builds libhdcpsdk.so (the HDCP SDK library) plus the SDK header and
pkg-config file. The hdcpd daemon is gated behind HDCP_BUILD_DAEMON=OFF
because it depends on Wayland/EGL client headers and a systemd unit that
are not available on HarmonyOS.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class IntelHdcpConan(ConanFile):
    name = "intel-hdcp"
    version = "21.2.0"
    description = "Intel Unified HDCP SDK — High-bandwidth Digital Content Protection SDK library and API"
    license = "MIT"
    homepage = "https://github.com/intel/hdcp"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The upstream CMake configure step runs find_package(OpenSSL REQUIRED)
        # (common/CMakeLists.txt), so openssl must resolve at configure time.
        self.requires("openssl/3.5.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Daemon requires Wayland/EGL client headers + systemd (not available on
        # HarmonyOS); ship the SDK library only.
        tc.variables["HDCP_BUILD_DAEMON"] = "OFF"
        # Upstream declares cmake_minimum_required(2.8.12); current CMake removed
        # compatibility below 3.5 — keep the upstream manifest untouched and let
        # CMake apply its own compatibility shim (repo-wide convention, e.g.
        # airspy/actor-framework use the same variable).
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Upstream install() references versioned artifacts
        # (libhdcpsdk.so.0 / libhdcpsdk.so.0.1.1) that the OHOS clang toolchain
        # does not produce (single unversioned libhdcpsdk.so, no SONAME), so the
        # stock cmake.install() fails. Collect the produced artifacts directly;
        # with cmake_layout() self.build_folder already points at
        # <base>/build/Release where the built .so and .pc live.
        build_dir = self.build_folder
        copy(self, "hdcpapi.h", src=os.path.join(self.source_folder, "sdk"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libhdcpsdk.so", src=build_dir,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libhdcpsdk.pc", src=build_dir,
             dst=os.path.join(self.package_folder, "lib", "pkgconfig"))
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "IntelHdcp")
        self.cpp_info.set_property("cmake_target_name", "IntelHdcp::IntelHdcp")
        self.cpp_info.set_property("pkg_config_name", "libhdcpsdk")
        self.cpp_info.libs = ["hdcpsdk"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]