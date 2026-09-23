#!/usr/bin/env python3
"""Conan recipe — posixsignalmanager 0.3.1 (POSIX signal management for Qt5)"""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import MesonToolchain
from conan.tools.layout import basic_layout

class PosixsignalmanagerConan(ConanFile):
    name = "posixsignalmanager"
    version = "0.3.1"
    description = "Library for safe, synchronous and asynchronous handling of POSIX signals for Qt applications"
    license = "BSL-1.0"
    homepage = "https://github.com/OpenSourceKakaxi/posixsignalmanager"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("qt/5.15.19")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["qt"] = "qt5"
        tc.project_options["tests"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        env_prefix = (
            "PATH=/data/service/hnp/bin:"
            "/storage/Users/currentUser/.opendesk/interpreters/pip-global/bin:$PATH "
            "CC=/data/service/hnp/bin/clang "
            "CXX=/data/service/hnp/bin/clang++ "
            "AR=/data/service/hnp/bin/llvm-ar "
        )
        self.run(
            env_prefix
            + f"meson setup {self.build_folder} {self.source_folder} "
            "--buildtype=release -Dqt=qt5 -Dtests=false",
            cwd=self.build_folder, env="conanbuild",
        )
        self.run(
            f"PATH=/data/service/hnp/bin:"
            f"/storage/Users/currentUser/.opendesk/interpreters/pip-global/bin:$PATH "
            f"meson compile -C {self.build_folder}",
            env="conanbuild",
        )

    def package(self):
        self.run(
            f"PATH=/data/service/hnp/bin:"
            f"/storage/Users/currentUser/.opendesk/interpreters/pip-global/bin:$PATH "
            f"DESTDIR={self.package_folder} meson install -C {self.build_folder}",
            env="conanbuild",
        )
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["posixsignalmanager"]
        self.cpp_info.libdirs = ["lib", "usr/local/lib"]
        self.cpp_info.includedirs = ["include", "usr/local/include"]
