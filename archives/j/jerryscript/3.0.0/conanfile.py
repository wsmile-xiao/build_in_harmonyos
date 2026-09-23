#!/usr/bin/env python3
"""Conan recipe for the JerryScript 3.0.0 embeddable JavaScript engine."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class JerryScriptConan(ConanFile):
    name = "jerryscript"
    version = "3.0.0"
    description = "Ultra-lightweight JavaScript engine for the Internet of Things"
    license = "Apache-2.0"
    homepage = "https://github.com/jerryscript-project/jerryscript"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "jerry_ext": [True, False],
        "jerry_math": [True, False],
        "default_port_implementation": [True, False],
        "tool_cmdline": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "jerry_ext": True,
        "jerry_math": False,
        "default_port_implementation": True,
        "tool_cmdline": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )
        toolchain.variables["ENABLE_AMALGAM"] = False
        toolchain.variables["ENABLE_LTO"] = False
        toolchain.variables["ENABLE_STRIP"] = False
        toolchain.variables["ENABLE_COMPILE_COMMANDS"] = False
        toolchain.variables["JERRY_CMDLINE"] = bool(self.options.tool_cmdline)
        toolchain.variables["JERRY_EXT"] = bool(
            self.options.jerry_ext or self.options.tool_cmdline
        )
        toolchain.variables["JERRY_MATH"] = bool(self.options.jerry_math)
        toolchain.variables["JERRY_PORT"] = bool(
            self.options.default_port_implementation or self.options.tool_cmdline
        )
        toolchain.variables["UNITTESTS"] = False
        toolchain.variables["DOCTESTS"] = False
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # Static linking needs dependents after the libraries that reference
        # them: jerry-ext -> jerry-core -> jerry-port/jerry-math.
        libraries = []
        if self.options.jerry_ext or self.options.tool_cmdline:
            libraries.append("jerry-ext")
        libraries.append("jerry-core")
        if self.options.default_port_implementation or self.options.tool_cmdline:
            libraries.append("jerry-port")
        if self.options.jerry_math:
            libraries.append("jerry-math")

        self.cpp_info.libs = libraries
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "jerryscript")
        self.cpp_info.set_property("cmake_target_name", "jerryscript::jerryscript")
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
