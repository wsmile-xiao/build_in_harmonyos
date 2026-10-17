#!/usr/bin/env python3
"""Consumer test for libetonyek/0.1.1.

Builds the C++ consumer test against the installed package and runs it under
the package's runtime environment.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.cmake import CMake, cmake_layout


class LibetonyekTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libetonyek's headers expose librevenge types, so the consumer needs
        # it on the include path and link line as well.
        self.requires("librevenge/0.0.5")

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Neutralize ambient LD_LIBRARY_PATH (some CI workers point it at
        # a /usr/local/lib whose incompatible libxml2.so.16 breaks the
        # SDK's lld on every link — CI-021 build #48068).
        environment = Environment()
        environment.define("LD_LIBRARY_PATH", "")
        with environment.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        # Verdict by direct execution under conanrun: libxml2 is a shared
        # dependency and ctest does not inherit conan's runtime environment
        # (libabw / libodfgen / libetonyek 0.1.13 precedent).
        # On the OHOS device the consumer binary needs libc++_shared, which
        # the system provides at /system/lib64 (kconfig / audiocd precedent);
        # conanrun alone does not carry it on this host.
        if str(self.settings.os) == "OHOS":
            environment = Environment()
            environment.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            with environment.vars(self).apply():
                self.run(
                    os.path.join(self.cpp.build.bindirs[0],
                                 "test_libetonyek"),
                    env="conanrun")
        else:
            self.run(os.path.join(self.cpp.build.bindirs[0],
                                  "test_libetonyek"),
                     env="conanrun")
