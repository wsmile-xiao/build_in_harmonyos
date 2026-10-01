#!/usr/bin/env python3
"""Conan recipe - fex-emu 2608 (FEX-Emu, CMake, x86/x86-64 -> AArch64 emulator)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class FEXEmuConan(ConanFile):
    name = "fex-emu"
    version = "2608"
    description = "Fast usermode x86 and x86-64 emulator for AArch64 (FEX-Emu)"
    license = "MIT"
    homepage = "https://fex-emu.com/"
    url = "https://github.com/FEX-Emu/FEX"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def build_requirements(self):
        # FEXCore's ASM regression suite assembles guest x86-64 snippets with NASM.
        self.tool_requires("nasm/2.16.03")

    def source(self):
        fex = self.conan_data["sources"]["fex"]
        get(self, url=fex["url"], sha256=fex["sha256"], strip_root=True)

        # Materialize the git submodules the release tarball omits.
        for _, spec in sorted(self.conan_data["sources"]["vendored"].items()):
            get(
                self,
                url=spec["url"],
                sha256=spec["sha256"],
                destination=os.path.join(self.source_folder, spec["destination"]),
                strip_root=True,
            )

    def generate(self):
        tc = CMakeToolchain(self)
        # FEXConfig is a Qt front-end; Qt is not published in the artifact repository.
        tc.variables["BUILD_FEXCONFIG"] = False
        # Build FEXCore's own unit and ASM regression suites.
        tc.variables["BUILD_TESTING"] = True
        # LTO multiplies the build time of the JIT for no functional gain here.
        tc.variables["ENABLE_LTO"] = False
        # FEX's glibc allocator interposition cannot apply to the OHOS musl libc
        # and is only required for guest thunk execution, which is disabled.
        tc.variables["ENABLE_JEMALLOC_GLIBC_ALLOC"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.define_path("FEX_DATA_DIR", os.path.join(self.package_folder, "share", "fex-emu"))
