#!/usr/bin/env python3
"""Test package for girara — dlopen + dlsym real API test."""

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
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        if not dep.libdirs:
            raise ConanInvalidConfiguration(
                "No library directories found for girara dependency"
            )
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libgirara.so")
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = _ce.get("c", "clang")
        self.run(f'{cc} test.c -o test_probe {inc} -DTARGET_SO=\'"{so}"\' -ldl')

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        self.run("./test_probe", env="conanrun")
