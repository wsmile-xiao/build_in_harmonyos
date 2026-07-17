#!/usr/bin/env python3
"""Conan recipe for bcrypt (libbcrypt by rg3).

bcrypt password hash C library — a simple wrapper providing a reentrant
interface for the bcrypt password hashing algorithm.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BcryptConan(ConanFile):
    name = "bcrypt"
    version = "1.0"
    description = "bcrypt password hash C library"
    license = "BSD"
    homepage = "https://github.com/rg3/libbcrypt"
    url = ""

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # R9: Always use -j1
        # Run make in source directory where the Makefile is
        self.run(f"make -C {self.source_folder} CC={cc} -j1")

    def package(self):
        copy(self, "bcrypt.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "bcrypt.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        # Conan/CMake expects lib<name>.a; the Makefile produces bcrypt.a without lib prefix
        src = os.path.join(self.package_folder, "lib", "bcrypt.a")
        dst = os.path.join(self.package_folder, "lib", "libbcrypt.a")
        if os.path.exists(src):
            os.rename(src, dst)

    def package_info(self):
        self.cpp_info.libs = ["bcrypt"]
