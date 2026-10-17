#!/usr/bin/env python3
"""Conan test_package — garmintools 0.12.2 （Conan L1 消费者测试）

通过 self.dependencies 直接取 include/lib 路径，用 clang 编译+链接，
验证第三方使用者可用 <garmintools/garmin.h> 公开头文件调用公开 API：
garmin_lpid / garmin_gpid（协议映射）与 garmin_load（错误路径）。
"""
import os

from conan import ConanFile


class GarmintoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        incs, linkdirs, rpaths = [], [], []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            for p in _d.cpp_info.libdirs:
                if os.path.isdir(p):
                    linkdirs.append("-L" + p)
                    rpaths.append("-Wl,-rpath-link," + p)
        comp = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict)
        cc = comp.get("c", "/data/service/hnp/bin/clang")
        self.run(f'{cc} -c test.c -o test.o {" ".join(incs)}')
        self.run(f'{cc} test.o -o test_garmintools {" ".join(linkdirs)} {" ".join(rpaths)} '
                 f'-lgarmintools -lusb-1.0')

    def test(self):
        self.run("./test_garmintools", env="conanrun")