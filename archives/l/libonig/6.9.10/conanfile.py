#!/usr/bin/env python3
"""Conan recipe for the Oniguruma regular-expression library."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibonigConan(ConanFile):
    name = "libonig"
    version = "6.9.10"
    package_type = "library"

    description = "Regular expression library compatible with POSIX and Perl syntax"
    license = "BSD-2-Clause"
    homepage = "https://github.com/kkos/oniguruma"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libonig is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TEST"] = True
        tc.variables["INSTALL_DOCUMENTATION"] = False
        tc.variables["INSTALL_EXAMPLES"] = False
        if self.settings.os == "OHOS":
            tc.variables["OHOS_ARCH"] = (
                "arm64-v8a" if str(self.settings.arch) == "armv8" else "x86_64"
            )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            test_dir = os.path.join(self.build_folder, "test")
            for executable in (
                "test_utf8",
                "test_syntax",
                "test_options",
                "testc",
                "testcu",
                "test_regset",
                "test_back",
            ):
                self.run(f"./{executable}", cwd=test_dir, env="conanrun")

    def package(self):
        CMake(self).install()
        # Keep this archive a pure library package. The upstream onig-config
        # script is a build helper, not a runtime tool, so it is not published.
        config_tool = os.path.join(self.package_folder, "bin", "onig-config")
        if os.path.isfile(config_tool):
            os.remove(config_tool)
        copy(self, "COPYING", src=self.source_folder,
             dst=self.package_folder + "/licenses")

    def package_info(self):
        self.cpp_info.libs = ["onig"]
        self.cpp_info.set_property("cmake_file_name", "onig")
        self.cpp_info.set_property("cmake_target_name", "onig::onig")
        self.cpp_info.set_property("pkg_config_name", "oniguruma")
