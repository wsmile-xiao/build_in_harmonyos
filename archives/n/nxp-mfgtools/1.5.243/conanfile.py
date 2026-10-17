#!/usr/bin/env python3
"""Conan recipe for nxp-mfgtools (uuu) — NXP Universal Update Utility.

USB firmware deployment tool for NXP i.MX chips.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import Environment
import os


class NxpMfgtoolsConan(ConanFile):
    name = "nxp-mfgtools"
    version = "1.5.243"
    description = "NXP Universal Update Utility (uuu) — USB firmware deployment tool for i.MX chips"
    license = "BSD-3-Clause"
    homepage = "https://github.com/nxp-imx/mfgtools"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusb/1.0.27")
        self.requires("bzip2/1.0.8")
        self.requires("zstd/1.5.7.1")
        self.requires("openssl/3.5.6.1.1")
        self.requires("zlib/1.3.2")
        self.requires("tinyxml2/11.0.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Create .tarball-version file so gen_ver.sh can generate gitversion.h
        save(self, ".tarball-version", self.version)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        pc = PkgConfigDeps(self)
        pc.generate()
        tc = CMakeToolchain(self)
        tc.generate()
        # Add OHOS SDK lib to LD_LIBRARY_PATH so lld linker can find libxml2.so.16
        env = Environment()
        cc = self.conf.get("tools.build:compiler_executables", default={})
        c_path = cc.get("c", "") if isinstance(cc, dict) else ""
        if c_path:
            sdk_lib = os.path.join(os.path.dirname(os.path.realpath(c_path)), "..", "lib")
            if os.path.isdir(sdk_lib):
                env.append_path("LD_LIBRARY_PATH", sdk_lib)
        env.vars(self).save_script("conan_ld_path")

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
