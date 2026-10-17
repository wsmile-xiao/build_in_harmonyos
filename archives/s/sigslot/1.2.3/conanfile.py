#!/usr/bin/env python3
"""Conan recipe for sigslot 1.2.3."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
from conan.tools.scm import Version


class SigslotConan(ConanFile):
    name = "sigslot"
    version = "1.2.3"
    description = "Type-safe, header-only C++14 signal-slot implementation"
    license = "MIT"
    homepage = "https://github.com/palacaze/sigslot"
    url = "https://github.com/conan-io/conan-center-index"
    topics = ("signals", "slots", "header-only", "observer", "cpp14")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"

    _min_cppstd = "14"
    _compilers_minimum_version = {
        "gcc": "5",
        "clang": "3.4",
        "apple-clang": "10",
        "Visual Studio": "15",
        "msvc": "191",
    }

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        self.info.clear()

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)

        minimum_version = self._compilers_minimum_version.get(
            str(self.settings.compiler)
        )
        if minimum_version and Version(self.settings.compiler.version) < Version(
            minimum_version
        ):
            raise ConanInvalidConfiguration(
                "sigslot requires {} {} or later".format(
                    self.settings.compiler, minimum_version
                )
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["SIGSLOT_COMPILE_EXAMPLES"] = False
        tc.cache_variables["SIGSLOT_COMPILE_TESTS"] = True
        tc.cache_variables["SIGSLOT_ENABLE_INSTALL"] = False
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # The upstream target is EXCLUDE_FROM_ALL and must be requested explicitly.
        cmake.build(target="sigslot-tests", cli_args=["--parallel", "1"])
        cmake.test()

    def package(self):
        copy(
            self,
            "*.hpp",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=True,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "PalSigslot")
        self.cpp_info.set_property("cmake_target_name", "Pal::Sigslot")
        self.cpp_info.set_property("pkg_config_name", "sigslot")
        if self.settings.os in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.system_libs = ["pthread"]
