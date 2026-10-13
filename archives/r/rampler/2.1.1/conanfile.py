#!/usr/bin/env python3
"""Conan recipe — rampler 2.1.1 (FASTA/Q subsampling tool).

M2 knowledge: the upstream tag archive carries `.gitmodules` with EMPTY
`vendor/bioparser/` content (submodule not shipped).  rampler's CMakeLists
resolves both vendored deps with `find_package(<pkg> <ver> QUIET)` first and
only falls back to FetchContent (git clone) when not found — so declaring the
already-published conan packages (bioparser/3.0.15, biosoup/0.10.0) plus
CMakeDeps makes find_package succeed and the missing submodule is never
touched.  See DRAFT-rampler-2.1.1-find-package-preferred-over-vendored-submodule.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RamplerConan(ConanFile):
    name = "rampler"
    version = "2.1.1"
    description = "Subsampling and splitting of FASTA/Q files"
    license = "MIT"
    homepage = "https://github.com/rvaser/rampler"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Both are already published in the ohpcd remote; they satisfy the
        # upstream find_package() calls so FetchContent is never reached.
        self.requires("bioparser/3.0.15")
        self.requires("biosoup/0.10.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
