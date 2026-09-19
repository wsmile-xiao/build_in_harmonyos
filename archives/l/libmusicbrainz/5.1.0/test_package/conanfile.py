#!/usr/bin/env python3
"""Conan consumer test for libmusicbrainz 5.1.0 — CMetadata 构造 + getter 冒烟。"""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["libmusicbrainz"].package_folder
        neon = self.dependencies["neon"].package_folder
        xml = self.dependencies["libxml2"].package_folder
        cc = os.environ.get("CXX", "clang++")
        src = os.path.join(self.source_folder, "test_musicbrainz.cpp")
        self.run(
            f"{cc} -std=c++11 -o test_musicbrainz {src} "
            f"-I{pkg}/include -I{neon}/include -I{xml}/include/libxml2 "
            f"-L{pkg}/lib -L{neon}/lib -L{xml}/lib "
            f"-lmusicbrainz5 -lneon -lxml2 -lm",
            env="conanbuild",
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link only")
            return
        # 运行时注入共享库路径（libmusicbrainz5/neon/libxml2 均为 shared 包）
        env = Environment()
        for dep in ("libmusicbrainz", "neon", "libxml2"):
            libdir = os.path.join(self.dependencies[dep].package_folder, "lib")
            env.prepend_path("LD_LIBRARY_PATH", libdir)
        with env.vars(self).apply():
            self.run("./test_musicbrainz", env="conanrun")
