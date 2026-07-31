#!/usr/bin/env python3
"""Conan recipe for EditorConfig Core C 0.12.9 (CMake)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    rm,
    rmdir,
    save,
)


class EditorconfigConan(ConanFile):
    name = "editorconfig"
    version = "0.12.9"
    description = "C library and command-line tool for EditorConfig parsing"
    license = "BSD-2-Clause"
    homepage = "https://editorconfig.org/"
    url = "https://github.com/editorconfig/editorconfig-core-c"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"EditorConfig Core C supports Linux and OHOS, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("pcre2/10.45")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["core"], strip_root=True)
        get(
            self,
            **self.conan_data["sources"]["tests"],
            destination=os.path.join(self.source_folder, "tests"),
            strip_root=True,
        )
        apply_conandata_patches(self)

    def generate(self):
        pcre2_root = self.dependencies["pcre2"].package_folder
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_STATICALLY_LINKED_EXE"] = False
        tc.cache_variables["PCRE2_STATIC"] = True
        tc.cache_variables["PCRE2_INCLUDE_DIR"] = os.path.join(
            pcre2_root, "include"
        )
        tc.cache_variables["PCRE2_LIBRARY_RELEASE"] = os.path.join(
            pcre2_root, "lib", "libpcre2-8.a"
        )
        tc.cache_variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        tc.cache_variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        tc.cache_variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN/../lib"
        tc.cache_variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = False
        if self.settings.os == "OHOS":
            tc.preprocessor_definitions["UNIX"] = None
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not can_run(self):
            self.output.info(
                "cross-building: upstream CTest cases registered but cannot run"
            )
        else:
            cmake.ctest(cli_args=["--output-on-failure", "--no-tests=error"])

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        CMake(self).install()
        rm(
            self,
            "libeditorconfig_static.a",
            os.path.join(self.package_folder, "lib"),
        )
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

        pc_file = os.path.join(
            self.package_folder, "lib", "pkgconfig", "editorconfig.pc"
        )
        pc_lines = load(self, pc_file).splitlines()
        pc_lines = [
            "prefix=${pcfiledir}/../.." if line.startswith("prefix=") else line
            for line in pc_lines
        ]
        save(self, pc_file, "\n".join(pc_lines) + "\n")

    def package_info(self):
        self.cpp_info.libs = ["editorconfig"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "EditorConfig")
        self.cpp_info.set_property(
            "cmake_target_name", "EditorConfig::EditorConfig"
        )
        self.cpp_info.set_property("pkg_config_name", "editorconfig")
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
