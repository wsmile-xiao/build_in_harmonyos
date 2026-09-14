#!/usr/bin/env python3
"""Conan test_package for util-linux 2.42.

Compiles a consumer using libblkid (blkid_new_probe_from_filename),
verifying libblkid links + initializes.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class UtilLinuxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        incs, libdirs = [], []
        for _r, _d in self.dependencies.items():
            incs += _d.cpp_info.includedirs
            libdirs += _d.cpp_info.libdirs
        inc = " ".join("-I" + p for p in dict.fromkeys(incs))
        link = " ".join(["-L" + p for p in dict.fromkeys(libdirs)]
                        + ["-lblkid", "-luuid", "-lmount", "-lm"]
                        + ["-Wl,-rpath," + p for p in dict.fromkeys(libdirs)])
        cc = "clang++"
        for cand in ("clang++", os.environ.get("CXX", "")):
            if cand and shutil.which(cand):
                cc = cand
                break
        self.run(f"{cc} -std=c++17 test_util_linux.cpp -o test_util_linux_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only verifying compile+link")
            return
        self.run("./test_util_linux_probe", env="conanrun")
