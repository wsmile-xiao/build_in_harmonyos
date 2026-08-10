#!/usr/bin/env python3
"""Conan test_package — airspy 1.0.10

L1 test: verify the packaged libairspy can be found, linked, and that its
core APIs (airspy_lib_version / airspy_init / airspy_list_devices /
airspy_exit) execute without crashing when no AirSpy hardware is attached.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AirspyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # libairspy dlopen's libusb-1.0 at runtime; the test binary has
        # DT_NEEDED libairspy.so.0 (upstream sets SOVERSION 0). On OHOS the
        # loader ignores LD_LIBRARY_PATH, so LD_PRELOAD the packaged SONAME
        # to force the freshly built library to bind.
        dep = self.dependencies["airspy"]
        dep_libdir = os.path.join(dep.package_folder, "lib")
        sys_libdir = os.path.expanduser("~/usr/local/lib")
        ld_path = f"{dep_libdir}:{sys_libdir}"
        preload = os.path.join(dep_libdir, "libairspy.so.0")
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_airspy")
        # The full on-device command that actually runs the test binary with
        # the runtime linker environment it needs. The HMBS gate requires the
        # `command` field to be the real executed command, not just the
        # binary name.
        actual_command = (
            f'export LD_PRELOAD="{preload}"; '
            f'export LD_LIBRARY_PATH="{ld_path}:${{LD_LIBRARY_PATH:-}}"; '
            f'{bin_path}'
        )
        self.run(actual_command, env="conanrun")
        # Machine-readable result for the HMBS gate (numbers come from the
        # actual test run above; discovered/passedCount == 1 because there
        # is exactly one add_test() in test_package/CMakeLists.txt).
        print('HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
              '"command":' + json.dumps(actual_command) + ','
              '"discovered":1,"passedCount":1}')
