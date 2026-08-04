#!/usr/bin/env python3
"""Conan recipe for ninja-build 1.13.2."""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class NinjaBuildConan(ConanFile):
    name = "ninja-build"
    version = "1.13.2"
    description = "Small build system with a focus on speed"
    license = "Apache-2.0"
    homepage = "https://ninja-build.org/"
    url = "https://github.com/ninja-build/ninja"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        if self.settings.os == "Windows":
            basic_layout(self)
            self.folders.build = "."
        else:
            cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        if self.settings.os == "Windows":
            return

        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = "OFF"
        tc.cache_variables["NINJA_BUILD_BINARY"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "Windows":
            self._build_windows_bootstrap()
            return

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _build_windows_bootstrap(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp") or compilers.get("cxx") or shutil.which("g++") or "g++"
        compiler_dir = os.path.dirname(cxx) if os.path.isabs(cxx) else ""
        ar = shutil.which("ar") or (os.path.join(compiler_dir, "ar.exe") if compiler_dir else "ar")

        if compiler_dir:
            os.environ["PATH"] = compiler_dir + os.pathsep + os.environ.get("PATH", "")
        os.environ["CXX"] = cxx
        os.environ["AR"] = ar

        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        os.environ["TMP"] = tmp_dir
        os.environ["TEMP"] = tmp_dir

        self.run(
            f'"{sys.executable}" configure.py --bootstrap --platform=mingw --host=mingw',
            cwd=self.source_folder,
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        if self.settings.os == "Windows":
            copy(self, "ninja.exe", src=self.source_folder, dst=bin_dir, keep_path=False)
        else:
            cmake = CMake(self)
            cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
