#!/usr/bin/env python3
"""Conan recipe for yatm 0.9 (CMake application)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class YatmConan(ConanFile):
    name = "yatm"
    version = "0.9"
    description = "Command line audio player with time stretching and pitch control"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/mlang/yatm"
    url = "https://github.com/mlang/yatm"
    topics = ("audio", "player", "time-stretching", "cli")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps", "VirtualBuildEnv"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libao-pulse/1.2.2")
        self.requires("libmad/0.15.1b")
        self.requires("libsndfile/1.2.2")
        self.requires("soundtouch/2.0.0")
        self.requires("slang/2.3.3")
        self.requires("speex/1.2.1")
        self.requires("libogg/1.3.6")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"yatm is supported only on Linux/OHOS, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["CMAKE_BUILD_TYPE"] = str(self.settings.build_type)
        toolchain.extra_cxxflags.append("-Wno-register")
        toolchain.extra_exelinkflags.append("-Wl,--as-needed")
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        pc_dir = self.generators_folder
        os.environ["PKG_CONFIG_PATH"] = pc_dir
        os.environ["PKG_CONFIG_LIBDIR"] = pc_dir
        cmake = CMake(self)
        cmake.configure()
        # E074: HMDFS rejects GNU make's jobserver FIFO during parallel builds.
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.cpp_info.requires = [
            "libao-pulse::libao-pulse",
            "libmad::libmad",
            "libsndfile::libsndfile",
            "soundtouch::soundtouch",
            "slang::slang",
            "speex::speex",
            "libogg::libogg",
        ]
