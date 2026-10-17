#!/usr/bin/env python3
"""Conan recipe for foonathan/string_id 2.0-3.

The upstream project has no install() rules, so package() explicitly stages
the generated configuration header, public headers, and the built library.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class StringIdConan(ConanFile):
    name = "string_id"
    version = "2.0-3"
    description = "A small C++ library for hashed strings used as identifiers"
    license = "Zlib"
    homepage = "https://github.com/foonathan/string_id"
    url = "https://github.com/foonathan/string_id"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # string_id only uses the C++ standard library; it has no Conan deps.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["FOONATHAN_STRING_ID_DATABASE"] = True
        tc.variables["FOONATHAN_STRING_ID_MULTITHREADED"] = True
        # CMake 4 rejects the upstream minimum version 2.8 unless the
        # compatibility policy version is supplied explicitly.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

        # The upstream project has no add_test() entries. Keep the official
        # test entry point in the recipe (it is a successful no-test ctest),
        # and run the shipped example when the built target is runnable.
        self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanrun")
        if can_run(self):
            example = os.path.join(
                self.build_folder, "foonathan_string_id_example"
            )
            if self.options.shared:
                # The example links to the just-built shared object before
                # package_info()/VirtualRunEnv can expose a package path.
                self.run(
                    f'LD_LIBRARY_PATH="{self.build_folder}:$LD_LIBRARY_PATH" '
                    f'"{example}"',
                    env="conanrun",
                )
            else:
                self.run(example, env="conanrun")

    def package(self):
        include_dir = os.path.join(self.package_folder, "include")
        lib_dir = os.path.join(self.package_folder, "lib")
        license_dir = os.path.join(self.package_folder, "licenses")

        copy(self, "*.hpp", src=self.source_folder, dst=include_dir)
        copy(self, "config_impl.hpp", src=self.build_folder, dst=include_dir)
        copy(self, "LICENSE", src=self.source_folder, dst=license_dir)

        if self.options.shared:
            copy(
                self,
                "libfoonathan_string_id.so*",
                src=self.build_folder,
                dst=lib_dir,
            )
        else:
            copy(
                self,
                "libfoonathan_string_id.a",
                src=self.build_folder,
                dst=lib_dir,
            )

    def package_info(self):
        self.cpp_info.libs = ["foonathan_string_id"]
        self.cpp_info.set_property("cmake_file_name", "foonathan_string_id")
        self.cpp_info.set_property(
            "cmake_target_name", "foonathan_string_id::foonathan_string_id"
        )
