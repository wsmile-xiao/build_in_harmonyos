#!/usr/bin/env python3
"""Test package for libappimage.

Builds a small program against the conan package (via cpp_info, like the
other recipes in this repo) and runs it: appimage_get_type / appimage_get_md5 /
appimage_get_payload_offset checks on a regular file and on a crafted
Type-2 AppImage header (ELF magic + AI\\x02 at offset 8).
"""

import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        incs, linkdirs, rpaths = [], [], []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            for p in _d.cpp_info.libdirs:
                if os.path.isdir(p):
                    linkdirs.append("-L" + p)
                    rpaths.append("-Wl,-rpath," + p)
                    rpaths.append("-Wl,-rpath-link," + p)
        comp = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict)
        cc = comp.get("cpp", "/data/service/hnp/bin/clang++")
        self.run(
            '%s %s -o test_package %s %s %s -lappimage'
            % (cc, " ".join(incs), os.path.join(self.source_folder, "test_package.cpp"),
               " ".join(linkdirs), " ".join(rpaths)),
            env="conanbuild",
        )

    def test(self):
        self.run(os.path.join(self.build_folder, "test_package"), env="conanrun")
