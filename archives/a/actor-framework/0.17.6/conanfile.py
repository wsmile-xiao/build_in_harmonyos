#!/usr/bin/env python3
"""Conan recipe for C++ Actor Framework 0.17.6."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class ActorFrameworkConan(ConanFile):
    name = "actor-framework"
    version = "0.17.6"
    description = "An open-source implementation of the actor model for C++"
    license = "BSD-3-Clause OR BSL-1.0"
    homepage = "https://www.actor-framework.org/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_io": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_io": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"actor-framework supports Linux and OHOS, not {self.settings.os}"
            )
        check_min_cppstd(self, "11")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        toolchain.cache_variables["CAF_BUILD_STATIC_ONLY"] = not bool(
            self.options.shared
        )
        toolchain.cache_variables["CAF_BUILD_STATIC"] = False
        toolchain.cache_variables["CAF_BUILD_STATIC_RUNTIME"] = False
        toolchain.cache_variables["CAF_NO_IO"] = not bool(self.options.with_io)
        toolchain.cache_variables["CAF_NO_OPENSSL"] = True
        toolchain.cache_variables["CAF_NO_OPENCL"] = True
        toolchain.cache_variables["CAF_NO_PYTHON"] = True
        toolchain.cache_variables["CAF_NO_TOOLS"] = True
        toolchain.cache_variables["CAF_NO_EXAMPLES"] = True
        toolchain.cache_variables["CAF_NO_COMPILER_CHECK"] = True
        toolchain.cache_variables["CAF_NO_AUTO_LIBCPP"] = True
        toolchain.cache_variables["CAF_NO_UNIT_TESTS"] = (
            str(self.settings.os) == "OHOS"
        )
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self.run(
                f'ctest --test-dir "{self.build_folder}" '
                "--output-on-failure -j8 --timeout 60"
            )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        suffix = "" if self.options.shared else "_static"
        self.cpp_info.set_property("cmake_file_name", "actor-framework")

        core = self.cpp_info.components["core"]
        core.libs = [f"caf_core{suffix}"]
        core.set_property("cmake_target_name", "actor-framework::core")
        if str(self.settings.os) in ("Linux", "OHOS"):
            core.system_libs = ["pthread"]

        if self.options.with_io:
            io = self.cpp_info.components["io"]
            io.libs = [f"caf_io{suffix}"]
            io.requires = ["core"]
            io.set_property("cmake_target_name", "actor-framework::io")
