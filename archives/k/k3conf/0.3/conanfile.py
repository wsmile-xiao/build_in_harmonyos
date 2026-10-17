#!/usr/bin/env python3
"""Conan recipe for the TI K3 diagnostic command-line tool."""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy
from conan.tools.scm import Git


class K3confConan(ConanFile):
    name = "k3conf"
    version = "0.3"
    description = "Diagnostic utility for Texas Instruments K3 processors"
    license = "BSD-3-Clause"
    homepage = "https://git.ti.com/cgit/k3conf/k3conf/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        source = self.conan_data["sources"]
        # Keep Conan's source_folder itself intact while ensuring Git gets an
        # empty target; Conan may use it as the current working directory.
        os.makedirs(self.source_folder, exist_ok=True)
        for entry in os.scandir(self.source_folder):
            if entry.is_dir(follow_symlinks=False):
                shutil.rmtree(entry.path)
            else:
                os.unlink(entry.path)
        git = Git(self)
        git.clone(url=source["url"], target=self.source_folder)
        git.checkout(commit=source["commit"])

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        license_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(license_dir, exist_ok=True)
        copy(self, "LICENSE", src=self.source_folder, dst=license_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
