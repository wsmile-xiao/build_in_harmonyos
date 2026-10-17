#!/usr/bin/env python3
"""Consumer test for libabw/0.1.4.

Builds the C++ consumer test against the installed package and runs it, then
exercises the packaged conversion tools through the shell test.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.cmake import CMake, cmake_layout


class LibabwTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libabw's headers expose librevenge types, so the consumer needs it
        # on the include path and link line as well.
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
        # The executable is registered with ctest (see CMakeLists.txt) for
        # interactive use, but the verdict is taken by running it directly
        # under the package's runtime environment: libabw is a static library
        # that links a *shared* libxml2, and ctest does not inherit conan's
        # runtime environment, so a plain ctest run cannot resolve
        # xmlTextReader* at load time (device-verified:
        # "Error relocating ./test_libabw: xmlTextReaderConstName: symbol
        # not found").  Running it with env="conanrun" also prints every
        # individual assertion into the build log.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libabw"),
                 env="conanrun")
        # The package also ships conversion tools; drive one end to end.
        tool = os.path.join(self.dependencies["libabw"].package_folder,
                            "bin", "abw2text")
        script = os.path.join(os.path.dirname(__file__),
                              "test_libabw_cli.sh")
        self.run(f'sh "{script}" "{tool}"', env="conanrun")
