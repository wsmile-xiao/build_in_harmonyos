#!/usr/bin/env python3
"""Conan recipe for netdiscover 0.21."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get, save


class NetdiscoverConan(ConanFile):
    name = "netdiscover"
    version = "0.21"
    description = "Active and passive ARP reconnaissance tool"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/netdiscover-scanner/netdiscover"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("netdiscover supports POSIX platforms")

    def requirements(self):
        self.requires(
            "libpcap/1.10.6",
            transitive_headers=True,
            transitive_libs=True,
        )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        save(
            self,
            os.path.join(self.source_folder, "config.h"),
            '#define VERSION "0.21"\n',
        )

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["NETDISCOVER_SOURCE_DIR"] = self.source_folder.replace(
            "\\", "/"
        )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=self.export_sources_folder)
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
