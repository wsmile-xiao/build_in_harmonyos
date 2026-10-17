#!/usr/bin/env python3
"""Conan recipe — frugally-deep 0.20.0 (header-only CMake library).

frugally-deep is a header-only C++17 deep-learning inference library.
Upstream provides a CMake INTERFACE target (frugally-deep::fdeep) and
requires eigen, FunctionalPlus (fplus) and nlohmann_json at build/use time.
The upstream unit-test data generation needs Python TensorFlow/Keras which
is not available on OHOS aarch64 (see upstream-test ledger); this recipe
does not build upstream tests.  A HarmonyOS-specific consumer test
(ohos_special_test.cpp) plus the test_package consumer test cover the
public API (read_model_from_string + predict).
"""
from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
import os


class FrugallyDeepConan(ConanFile):
    name = "frugally-deep"
    version = "0.20.0"
    description = "frugally-deep - a header-only library for the inference of deep neural networks"
    license = "MIT"
    homepage = "https://github.com/Dobiasd/frugally-deep"
    url = "https://github.com/Dobiasd/frugally-deep"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # Upstream conanfile.txt pins eigen/3.4.0, functionalplus/v0.2.24,
        # nlohmann_json/3.11.3; the OHOS registry publishes the same libs as
        # eigen/3.4.0, fplus/0.2.28 (provides FunctionalPlus config), and
        # nlohmann_json/3.12.0.  Use the published versions (verified by
        # conan download --only-recipe / conan list, see test report L0i).
        self.requires("eigen/3.4.0")
        self.requires("fplus/0.2.28")
        self.requires("nlohmann_json/3.12.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Header-only: no compilation needed.

    def package(self):
        # Header-only: copy include tree into package
        copy(self, pattern="*",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, pattern="LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "frugally-deep")
        self.cpp_info.set_property("cmake_target_name", "frugally-deep::frugally-deep")
        # Forward direct header-only deps (validators require explicit use).
        self.cpp_info.requires = [
            "eigen::eigen",
            "fplus::fplus",
            "nlohmann_json::nlohmann_json",
        ]