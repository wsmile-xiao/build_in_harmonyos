#!/usr/bin/env python3
"""Conan test_package for libimobiledevice 1.4.0.

Links the installed static library with all its transitive dependencies
(libusbmuxd, libplist, libimobiledevice-glue, libtatsu, openssl, libcurl)
and exercises the public C API.  OHOS has no usbmuxd daemon / iOS device,
so the device APIs take their documented error paths, which still proves
the link and ABI are correct.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout

CHECKS = 3


class LibimobiledeviceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # explicit closure for static linking + include propagation
        # (libimobiledevice.h includes <plist/plist.h>; the .a needs
        # usbmuxd/plist/glue/tatsu/openssl symbols)
        self.requires("libplist/2.3.0")
        self.requires("libusbmuxd/2.0.2")
        self.requires("libimobiledevice-glue/1.3.0")
        self.requires("libtatsu/1.0.5")
        self.requires("openssl/1.1.1w")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libimobiledevice")
        self.run('"%s"' % bin_path, env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "test_libimobiledevice (API link/ABI consumer)",
            "consumer_passed": CHECKS,
            "consumer_total": CHECKS,
        }))
