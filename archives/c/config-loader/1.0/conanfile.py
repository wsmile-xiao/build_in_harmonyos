#!/usr/bin/env python3
"""Conan recipe — config-loader 1.0 (CMake, header-first + static lib).

A C++17 config-file loader (JSON/XML/YAML) with reflection-style schema
macros (DEFINE_SCHEMA). Upstream CMake pulls three parser deps plus Catch2
via git submodules; this recipe satisfies them from the OHOS Conan registry
instead, patching ThirdParty.cmake to use find_package.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class ConfigLoaderConan(ConanFile):
    name = "config-loader"
    version = "1.0"
    package_type = "library"
    license = "MIT"
    homepage = "https://github.com/netcan/config-loader"
    url = "https://github.com/netcan/config-loader"
    description = "A C++17 config file loader (JSON/XML/YAML) with reflection-style schema macros"
    topics = ("config", "json", "xml", "yaml", "reflection", "deserialize")

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # Parser backends (upstream git submodules -> Conan registry deps).
        # R36: all three are already published on ohpcd.
        self.requires("tinyxml2/10.0.0")
        self.requires("jsoncpp/1.9.8.1")
        self.requires("yaml-cpp/0.9.0")
        # Catch2 v3 is required by the upstream unit-test suite (test/ut),
        # which runs as CTest during `conan create`.
        self.requires("catch2/3.16.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # Keep the three parser backends enabled (upstream defaults).
        tc.variables["HAS_TINYXML2"] = True
        tc.variables["HAS_JSONCPP"] = True
        tc.variables["HAS_YAMLCPP"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"], build_tool_args=["-j1"])
        # Run the upstream Catch2 suite registered as CTest in test/ut.
        cmake.test(cli_args=["--parallel", "1"], build_tool_args=["-j1"])

    def package(self):
        # After the ThirdParty.cmake patch the parser/tests deps come from
        # find_package (no add_subdirectory), so cmake.install() installs only
        # config-loader's own lib + headers.
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Upstream CMake propagates HAS_* parser macros PUBLIC; export them so
        # consumers build the real parsers instead of UnsupportedParser.
        # (Parser headers are public; consumers link tinyxml2/jsoncpp/yaml-cpp
        # themselves, as test_package does.)
        self.cpp_info.libs = ["config-loader"]
        self.cpp_info.defines = ["HAS_TINYXML2", "HAS_JSONCPP", "HAS_YAMLCPP"]