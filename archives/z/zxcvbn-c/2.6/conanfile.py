#!/usr/bin/env python3
"""Conan recipe for zxcvbn-c 2.6.

The upstream CMake project generates its dictionary data at build time and
does not define install rules.  The package step therefore copies the
selected library and public header directly from the CMake build tree.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ZxcvbnCConan(ConanFile):
    name = "zxcvbn-c"
    version = "2.6"
    description = "C/C++ implementation of the zxcvbn password strength estimator"
    license = "MIT"
    homepage = "https://github.com/tsyrogit/zxcvbn-c"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zxcvbn-c has no third-party dependencies.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # The upstream project declares both library variants explicitly;
        # keep the option for package selection while preserving that build.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Upstream declares the same generated dictionary headers independently
        # for several targets. OHOS make can race while writing those files.
        cmake.build(build_tool_args=["-j1"])
        # The upstream `test` target invokes several programs without
        # arguments; those programs read stdin and hang in Conan's non-
        # interactive build environment. Run the same checks explicitly with
        # the upstream testcase file instead.
        if can_run(self):
            test_dir = self.build_folder
            testcases = os.path.join(self.source_folder, "testcases.txt")
            self.run(os.path.join(test_dir, "test-internals"),
                     cwd=test_dir, env="conanbuild")
            for name in (
                "test-file", "test-inline", "test-c++file",
                "test-c++inline", "test-shlib", "test-statlib",
            ):
                command = (
                    f'"{os.path.join(test_dir, name)}" -t "{testcases}"'
                )
                if name == "test-shlib":
                    command = (
                        f'LD_LIBRARY_PATH="{test_dir}:$LD_LIBRARY_PATH" '
                        + command
                    )
                self.run(
                    command, cwd=test_dir, env="conanbuild"
                )

    def package(self):
        copy(self, "zxcvbn.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

        if self.options.shared:
            copy(self, "libzxcvbn.so*", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"))
            copy(self, "libzxcvbn.dylib*", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"))
            copy(self, "zxcvbn.dll", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "bin"))
            copy(self, "zxcvbn.lib", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libzxcvbn.a", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"))
            copy(self, "zxcvbn.lib", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["zxcvbn"]
        self.cpp_info.set_property("cmake_file_name", "zxcvbn-c")
        self.cpp_info.set_property("cmake_target_name", "zxcvbn-c::zxcvbn-c")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
