#!/usr/bin/env python3
"""Test package for girara — consumer test with standard include + direct linking."""

import glob
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["girara"].cpp_info
        if not dep.libdirs:
            raise ConanInvalidConfiguration(
                "No library directories found for girara dependency"
            )
        incs, libflags = [], []
        for _ref, _d in self.dependencies.items():
            for p in _d.cpp_info.includedirs:
                incs.append("-I" + p)
            for ld in _d.cpp_info.libdirs:
                libflags += ["-L" + ld, "-Wl,-rpath," + ld]
        # girara 公共头文件（datastructures.h）依赖 glib.h/glibconfig.h；
        # 间接依赖返回相对 includedirs，需从 conan 缓存定位 glib（兼容本机与 CI 两种缓存布局）
        home = os.path.expanduser("~")
        cache_roots = [
            os.path.join(home, ".conan2"),
            os.path.join(home, ".cache", "conan2"),
        ]
        for root in cache_roots:
            for g in sorted(glob.glob(os.path.join(root, "p", "glib*", "p", "include", "glib-2.0"))):
                incs.append("-I" + g)
            for gc in sorted(glob.glob(os.path.join(root, "p", "glib*", "p", "lib", "glib-2.0", "include"))):
                incs.append("-I" + gc)
            for gl in sorted(glob.glob(os.path.join(root, "p", "glib*", "p", "lib"))):
                libflags += ["-L" + gl, "-Wl,-rpath," + gl]
        inc = " ".join(incs)
        lib = " ".join(libflags)
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = _ce.get("c", "clang")
        # 标准消费者方式：include 头文件 + 直接链接 libgirara.so
        self.run(f"{cc} test.c -o test_probe {inc} {lib} -lgirara -ldl")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        self.run("./test_probe", env="conanrun")
