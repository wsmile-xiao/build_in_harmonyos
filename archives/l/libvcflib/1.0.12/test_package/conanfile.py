#!/usr/bin/env python3
"""Conan test_package — libvcflib/1.0.12 consumer test.

Builds a real consumer against the installed package (headers + static archives) and
runs it on a small VCF fixture.  See MANIFEST.yml for the assertion inventory.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibvcflibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # Same reasoning as the library recipe: do not inherit os.cpu_count() (20 on
        # the OHOS device) for the two-translation-unit consumer.
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libvcflib")
        fixture = os.path.join(self.source_folder, "test.vcf")

        # The consumer must be able to run against the installed layout only.
        self.run(f'"{binary}" "{fixture}"', env="conanrun")

        # Installed layout: static archives and the public headers must be present.
        pkg = self.dependencies[self.tested_reference_str].package_folder
        libvcflib_a = os.path.join(pkg, "lib", "libvcflib.a")
        libwfa2_a = os.path.join(pkg, "lib", "libwfa2.a")
        variant_h = os.path.join(pkg, "include", "vcflib", "Variant.h")
        tabix_hpp = os.path.join(pkg, "include", "vcflib", "tabix.hpp")
        leftalign_hpp = os.path.join(pkg, "include", "vcflib", "LeftAlign.hpp")
        self.output.info(f"[layout] {libvcflib_a}")
        self.output.info(f"[layout] {libwfa2_a}")
        self.output.info(f"[layout] {variant_h}")
        self.output.info(f"[layout] {tabix_hpp}")
        self.output.info(f"[layout] {leftalign_hpp}")
        assert os.path.isfile(libvcflib_a), f"missing static archive {libvcflib_a}"
        assert os.path.isfile(libwfa2_a), f"missing static archive {libwfa2_a}"
        assert os.path.isfile(variant_h), f"missing public header {variant_h}"
        assert os.path.isfile(tabix_hpp), f"missing public header {tabix_hpp}"
        assert os.path.isfile(leftalign_hpp), f"missing public header {leftalign_hpp}"
