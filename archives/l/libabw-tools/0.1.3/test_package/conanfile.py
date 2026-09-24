#!/usr/bin/env python3
"""Consumer test for libabw-tools/0.1.3.

Builds the C++ consumer test against the installed package (the tools
package ships the libabw static library and headers) and runs it, then
exercises the packaged conversion tools (abw2text / abw2html / abw2raw)
end to end through the shell test.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.cmake import CMake, cmake_layout


class LibabwToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # The package is package_type="static-library", which propagates
        # headers/libs downstream by default; declare them explicitly anyway
        # so CMakeDeps renders the libabw target with its include dirs and
        # library for the API test.
        self.requires(self.tested_reference_str, headers=True, libs=True)
        # libabw's public headers expose librevenge types (RVNGInputStream),
        # so the consumer needs it on the include path and link line too.
        self.requires("librevenge/0.0.5")

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Neutralize ambient LD_LIBRARY_PATH (some CI workers point it at a
        # /usr/local/lib whose incompatible libxml2 breaks the SDK's lld on
        # every link).
        environment = Environment()
        environment.define("LD_LIBRARY_PATH", "")
        with environment.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def generate(self):
        from conan.tools.cmake import CMakeToolchain
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_VERBOSE_MAKEFILE"] = "ON"
        tc.generate()

    def test(self):
        # The executable is registered with ctest (see CMakeLists.txt) for
        # interactive use, but the verdict is taken by running it directly
        # under the package's runtime environment: libabw is a static
        # library that links a *shared* libxml2, and ctest does not inherit
        # conan's runtime environment, so a plain ctest run cannot resolve
        # xmlTextReader* at load time.  Running it with env="conanrun" also
        # prints every individual assertion into the build log.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libabw_tools"),
                 env="conanrun")
        # Drive the installed conversion tools end to end.
        package_bin = os.path.join(self.dependencies[self.tested_reference_str]
                                   .package_folder, "bin")
        script = os.path.join(os.path.dirname(__file__), "test_libabw_cli.sh")
        self.run(f'sh "{script}" "{package_bin}"', env="conanrun")
