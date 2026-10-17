#!/usr/bin/env python3
"""Conan test_package — libsigcplusplus 3.8.1.

Compiles and runs a C++17 consumer against the packaged libsigc-3.0 that
exercises the real signals/slots API: signal connect/emit, default
last-value collector, connection lifetime, scoped_connection, trackable
auto-disconnect, ptr_fun/mem_fun/bind slots and exception_catch adaptor.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibsigcplusplusTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # OHOS: /system/bin/sh (mksh) cannot exec ELF; wrap with the
            # CONFIG_SHELL bash (atkmm/libsigc-2 style) and assemble
            # LD_LIBRARY_PATH explicitly from every dependency libdir plus
            # the SDK libc++_shared.so location (not a Conan package).
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            libs = []
            for _ref, _dep in self.dependencies.items():
                libs += list(_dep.cpp_info.libdirs)
            _sdk_libcxx = (
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos"
                "/native/llvm/lib/aarch64-linux-ohos"
            )
            if os.path.isdir(_sdk_libcxx):
                libs.append(_sdk_libcxx)
            ld_path = ":".join(dict.fromkeys(l for l in libs if l))
            exe = os.path.join(self.cpp.build.bindirs[0], "test_libsigcplusplus")
            self.run(
                f'{bash} -c \'export LD_LIBRARY_PATH="{ld_path}"; "{exe}"\'',
                env="conanrun",
            )
        else:
            self.output.info("cross-building: consumer linked but cannot run")
