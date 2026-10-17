#!/usr/bin/env python3
"""Conan recipe — cado (Capability Ambient DO) 0.9.6."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.build import cross_building


class CadoConan(ConanFile):
    name = "cado"
    version = "0.9.6"
    description = "CADO — Capability Ambient DO. Provide users just the capabilities they need"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/rd235/cado"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    requires = (
        "libcap/2.73",
        "linux-pam/1.7.2",
        "mhash/0.9.9.9",
        "libexecs/1.4",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("cado requires a POSIX C target")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        # find_library 依赖库：CMakeToolchain 已设置 CMAKE_PREFIX_PATH 包含
        # 所有依赖 package，find_library 会在各 prefix 的 lib 目录搜索 cap/
        # execs/mhash/pam/pam_misc，无需手动注入 CMAKE_LIBRARY_PATH。
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
