#!/usr/bin/env python3
"""Conan recipe for rig 1.11."""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RigConan(ConanFile):
    name = "rig"
    version = "1.11"
    description = "Random identity generator for test data"
    license = "GPL-2.0-or-later"
    homepage = "http://rig.sourceforge.net/"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        default_cxx = {
            "gcc": "g++",
            "clang": "clang++",
        }.get(str(self.settings.compiler), "c++")
        cxx = compilers.get("cpp", default_cxx) if compilers else default_cxx
        build_type_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }
        cxxflags = f"-fPIC {build_type_flags.get(str(self.settings.build_type), '-O2 -DNDEBUG')}"
        self.run(
            f'make CXX="{cxx}" CXXFLAGS="{cxxflags}" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "rig", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "*.idx", src=os.path.join(self.source_folder, "data"),
             dst=os.path.join(self.package_folder, "share", "rig"), keep_path=False)
        copy(self, "rig.6", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man6"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        bin_path = os.path.join(self.package_folder, "bin", "rig")
        if os.path.exists(bin_path):
            os.chmod(bin_path, 0o755)
        if os.path.exists(bin_path) and str(self.settings.os) == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            tmp_signed = bin_path + ".signed"
            subprocess.run(
                [
                    sign_tool,
                    "sign",
                    "-inFile",
                    bin_path,
                    "-outFile",
                    tmp_signed,
                    "-selfSign",
                    "1",
                ],
                check=True,
            )
            os.replace(tmp_signed, bin_path)
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.bindirs = ["bin"]
