#!/usr/bin/env python3
"""Conan recipe — CrazyWa 0.0.0-git2019.06.13 (CMake)."""
import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, check_sha256, copy, export_conandata_patches


class CrazywaConan(ConanFile):
    name = "crazywa"
    version = "0.0.0-git2019.06.13"
    license = "GPL-3.0-or-later"
    homepage = "https://hgm.nubati.net/"
    description = "XBoard engine for chess and shogi variants with piece drops"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        for pattern in ("CMakeLists.txt", "COPYING", "test_package/protocol_test.py"):
            copy(self, pattern, src=self.recipe_folder, dst=self.export_sources_folder)
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        upstream = os.path.join(self.source_folder, "upstream")
        self.run("git clone " + shlex.quote(source["url"]) + " " + shlex.quote(upstream))
        self.run("git -c " + shlex.quote("safe.directory=" + upstream) +
                 " -C " + shlex.quote(upstream) + " checkout --detach " + source["commit"])
        check_sha256(self, os.path.join(upstream, "dropper.c"), source["sha256"])

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        executable = os.path.join(self.build_folder, "crazywa")
        if self.settings.os == "OHOS":
            self.run("binary-sign-tool sign -inFile " + shlex.quote(executable) +
                     " -outFile " + shlex.quote(executable + ".signed") + " -selfSign 1")
            os.replace(executable + ".signed", executable)
            os.chmod(executable, 0o755)
        # Upstream has no test suite; run the added protocol regression cases.
        test = os.path.join(self.source_folder, "test_package", "protocol_test.py")
        self.run("python3 " + shlex.quote(test) + " " + shlex.quote(executable), env="conanrun")

    def package(self):
        copy(self, "crazywa", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "crazywa.pod", src=os.path.join(self.source_folder, "upstream"),
             dst=os.path.join(self.package_folder, "share", "doc", "crazywa"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
