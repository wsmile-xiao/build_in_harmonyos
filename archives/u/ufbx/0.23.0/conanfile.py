#!/usr/bin/env python3
"""Conan recipe — ufbx 0.23.0

Single-file C library (fbx parser). Build system: none (compile ufbx.c directly).
License: MIT (see LICENSE in upstream repo).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class UfbxConan(ConanFile):
    name = "ufbx"
    version = "0.23.0"
    description = "Lightweight, single-file C library to load and interact with FBX files"
    license = "MIT"
    homepage = "https://github.com/ufbx/ufbx"
    url = ""  # CI fills this
    topics = ("fbx", "3d", "parser", "single-file")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # ufbx is a single-file C99 library: compile ufbx.c into libufbx.a
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        cflags = "-O2 -fPIC -std=c99"
        if self.settings.compiler == "clang":
            cflags += " -fvisibility=hidden"
        self.run(f'{cc} {cflags} -c ufbx.c -o ufbx.o', cwd=self.source_folder)
        ar = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("ar") or "llvm-ar"
        self.run(f'{ar} rcs libufbx.a ufbx.o', cwd=self.source_folder)

        # Verify the library exports the public entry points
        self.run("nm libufbx.a | grep -q ufbx_load_memory", cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "libufbx.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "ufbx.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["ufbx"]
        self.cpp_info.set_property("cmake_file_name", "ufbx")
        self.cpp_info.set_property("cmake_target_name", "ufbx::ufbx")
        self.cpp_info.set_property("pkg_config_name", "ufbx")