#!/usr/bin/env python3
"""Conan consumer test for libmusicbrainz5 5.1.0-git20150707.

链接两个安装的库（musicbrainz5cc + musicbrainz5），验证 C++ / C API 可被
第三方工程编译、链接与调用（L1 消费者视角测试）。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["libmusicbrainz5"].package_folder
        neon = self.dependencies["neon"].package_folder
        xml = self.dependencies["libxml2"].package_folder

        cxx = os.environ.get("CXX", "clang++")
        src = os.path.join(self.source_folder, "test_musicbrainz5.cpp")

        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(xml, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(pkg, "lib"))
        with env.vars(self).apply():
            self.run(
                f"{cxx} -std=c++11 -o test_musicbrainz5 {src} "
                f"-I{pkg}/include -I{neon}/include -I{xml}/include/libxml2 "
                f"-L{pkg}/lib -L{neon}/lib -L{xml}/lib "
                f"-lmusicbrainz5 -lmusicbrainz5cc -lneon -lxml2 -lm",
                env="conanbuild",
            )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link only")
            return

        env = Environment()
        for dep in ("libmusicbrainz5", "neon", "libxml2"):
            libdir = os.path.join(self.dependencies[dep].package_folder, "lib")
            env.prepend_path("LD_LIBRARY_PATH", libdir)
        with env.vars(self).apply():
            self.run(os.path.join(self.build_folder, "test_musicbrainz5"),
                     env="conanrun")
