#!/usr/bin/env python3
"""Consumer test for libwps/0.4.11.

Builds the C++ consumer test against the installed package and runs it, then
exercises the packaged conversion tools through the shell test.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibwpsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libwps's public headers expose librevenge types, so the consumer
        # needs it on the include path and link line as well.
        self.requires("librevenge/0.0.5")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # ctest runs under the conanbuild environment, which carries the
        # profile's LD_LIBRARY_PATH; the direct runs below use conanrun,
        # which does not.  The test binary and the conversion tools are OHOS
        # target executables: their libc++.so (the __h-namespace build the
        # SDK links against) lives in /system/lib64, so that directory must
        # be on the loader path for the direct runs as well.
        environment = Environment()
        if os.path.isdir("/system/lib64"):
            environment.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with environment.vars(self).apply():
            # Run it once more directly so the individual assertion results
            # end up in the build log as evidence rather than only on
            # failure.
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_libwps"),
                     env="conanrun")
            # The package also ships conversion tools; drive one end to end.
            tool = os.path.join(self.dependencies["libwps"].package_folder,
                                "bin", "wps2text")
            script = os.path.join(os.path.dirname(__file__),
                                  "test_libwps_cli.sh")
            self.run(f'sh "{script}" "{tool}"', env="conanrun")
