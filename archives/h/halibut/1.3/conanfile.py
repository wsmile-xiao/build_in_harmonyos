#!/usr/bin/env python3
"""Conan recipe for halibut 1.3 — CMake-based documentation tool.

Halibut is a documentation production system, with elements similar to
TeX, debiandoc-sgml, TeXinfo, and others (MIT License).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class HalibutConan(ConanFile):
    name = "halibut"
    version = "1.3"
    description = "Halibut documentation production system"
    license = "MIT"
    homepage = "https://www.chiark.greenend.org.uk/~sgtatham/halibut/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4 removed compatibility with CMake < 3.5 policies
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []