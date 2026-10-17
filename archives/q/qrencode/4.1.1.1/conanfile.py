#!/usr/bin/env python3
"""Conan recipe for qrencode 4.1.1.1 (upstream 4.1.1) — QR Code library."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QrencodeConan(ConanFile):
    name = "qrencode"
    version = "4.1.1.1"
    description = "Fast and compact QR Code encoding library"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/fukuchi/libqrencode"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_tools": [True, False],
        "with_tests": [True, False],
        "without_png": [True, False],
    }
    default_options = {
        "shared": False,
        "with_tools": False,
        "with_tests": True,
        "without_png": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["WITH_TOOLS"] = bool(self.options.with_tools)
        tc.variables["WITH_TESTS"] = bool(self.options.with_tests)
        tc.variables["WITHOUT_PNG"] = bool(self.options.without_png)
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        cmake.build()
        if self.options.with_tests:
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if self.settings.os == "OHOS" and self.options.shared:
            self._sign_shared_objects()

    def _sign_shared_objects(self):
        """Sign OHOS ELF shared objects with the target's native signer."""
        objcopy = os.environ.get("OHOS_LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("OHOS_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _, files in os.walk(libdir):
            for name in files:
                if not (name.endswith(".so") or ".so." in name):
                    continue
                path = os.path.join(root, name)
                self.run('{0} --remove-section .codesign "{1}" 2>/dev/null || true'.format(objcopy, path))
                self.run('{0} sign -inFile "{1}" -outFile "{1}" -selfSign 1'.format(signer, path))

    def package_info(self):
        self.cpp_info.libs = ["qrencode"]
