#!/usr/bin/env python3
"""Conan recipe for the Ceph 20.2.2 CRUSH core library (CMake)."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class CephConan(ConanFile):
    name = "ceph"
    version = "20.2.2"
    description = "Standalone CRUSH data-placement component from Ceph"
    license = "LGPL-2.1-or-later"
    homepage = "https://ceph.com/"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    exports_sources = "files/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CEPH_SOURCE_DIR"] = self.source_folder.replace("\\", "/")
        # Cross builds cannot execute target binaries, but compiling the
        # adapted upstream tests still validates their OHOS compatibility.
        tc.variables["BUILD_TESTING"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(
            build_script_folder=os.path.join(self.export_sources_folder, "files")
        )
        cmake.build(cli_args=["--parallel", "1"])
        if not cross_building(self):
            cmake.test()
        else:
            self.output.info(
                "Cross-building: CRUSH tests compiled; runtime execution skipped"
            )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ceph")
        crush = self.cpp_info.components["crush"]
        crush.libs = ["ceph_crush"]
        if self.settings.os in ("Linux", "OHOS"):
            crush.system_libs = ["m"]
        crush.set_property("cmake_target_name", "ceph::crush")
        crush.set_property("pkg_config_name", "ceph-crush")
