#!/usr/bin/env python3
"""Conan recipe for libpog 0.5.3 - C++17 LALR(1) parser generator.

Pog splits a parser into token declarations (RE2 regular expressions) and
grammar rules over those tokens, and generates an LALR(1) parser.  The library
itself is header-only (``include/pog``) but requires RE2 (tokenizer) and fmt
(diagnostics/reports), which are not header-only.

OHOS notes
----------
* Header-only package: ``package()`` installs ``include/pog`` plus the license
  and the generated CMake/pkg-config files, and ``package_id()`` clears the
  binary settings.
* The upstream CMakeLists prefers its own ``cmake/Findre2.cmake`` /
  ``cmake/fmt/Findfmt.cmake`` (module mode).  ``CMAKE_FIND_PACKAGE_PREFER_CONFIG``
  is forced ON so the Conan-provided ``re2``/``fmt`` config packages are used
  instead.
* RE2 and fmt come from the Conan packages (``re2/2024-04-01``,
  ``fmt/8.1.1``) rather than the bundled ``deps/`` ExternalProject builds.
* The upstream test suite (132 ``TEST`` macros in ``tests/*.cpp``) is built with
  the bundled googletest (``POG_TESTS=ON``) and run on the device.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LibpogConan(ConanFile):
    name = "libpog"
    version = "0.5.3"
    description = "C++17 library for generating LALR(1) parsers (tokenizer + grammar rules)"
    license = "MIT"
    homepage = "https://github.com/metthal/pog"
    url = ""

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"

    no_copy_source = True

    def requirements(self):
        self.requires("re2/2024-04-01")
        self.requires("fmt/8.1.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libpog OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package_id(self):
        self.info.clear()

    def generate(self):
        # The project's CMake does find_package(re2)/find_package(fmt), so the
        # dependency config files must be generated for this build too.
        CMakeDeps(self).generate()
        # fmt is built as a shared library, so the test run needs its libdir.
        VirtualRunEnv(self).generate()
        toolchain = CMakeToolchain(self)
        # Use the Conan-provided re2/fmt config packages instead of the
        # project's Findre2.cmake / Findfmt.cmake module finders.
        toolchain.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = "ON"
        toolchain.cache_variables["POG_TESTS"] = "ON"
        toolchain.cache_variables["POG_PIC"] = "ON"
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        binary = os.path.join(self.build_folder, "tests", "pog_tests")
        log = os.path.join(self.build_folder, "upstream-pog-tests.log")
        self.run('"{}" > "{}" 2>&1'.format(binary, log), env="conanrun")
        with open(log, "r", errors="replace") as handle:
            content = handle.read()
        passed = 0
        for line in content.splitlines():
            match = re.match(r"\[  PASSED  \] (\d+) test", line)
            if match:
                passed = int(match.group(1))
        if passed <= 0:
            raise ConanException("upstream pog tests did not report any passing tests")
        self.output.info("upstream pog tests: {} passed".format(passed))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # pog headers include <re2/re2.h> and <fmt/...>; propagate the deps.
        self.cpp_info.requires = ["re2::re2", "fmt::fmt"]
        self.cpp_info.set_property("cmake_file_name", "pog")
        self.cpp_info.set_property("cmake_target_name", "pog::pog")
        self.cpp_info.set_property("pkg_config_name", "pog")
