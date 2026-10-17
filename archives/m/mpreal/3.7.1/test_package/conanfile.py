#!/usr/bin/env python3
"""Conan test_package — mpreal consumer verification (R34).

Compiles a C++ consumer against the installed <mpreal.h>, links the
transitive mpfr/gmp libraries from the dependency graph, asserts real
computed values, and executes the probe binary. Fails to build when the
package artifacts are removed (CI L1e destructive negative test).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class MprealTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cxx = os.environ.get("CXX", "clang++")
        incs, libdirs, libs = [], [], []
        for dep in self.dependencies.values():
            incs += list(dep.cpp_info.includedirs)
            libdirs += list(dep.cpp_info.libdirs)
            libs += ["-l" + l for l in dep.cpp_info.libs]
        flags = " ".join("-I" + i for i in incs)
        flags += " " + " ".join("-L" + d for d in libdirs)
        flags += " " + " ".join(libs)
        self.run(f"{cxx} -O2 -std=c++11 {flags} test.cpp -o test_probe")

    def test(self):
        # 真机/可运行环境执行断言；纯交叉构建如实跳过运行（编译+链接
        # 已在上一步验证，运行证据由设备 W3/G2 提供）。
        if can_run(self):
            self.run("./test_probe", env="conanrun")
        else:
            self.output.warning(
                "cross build: test_probe compiled and linked; execution "
                "skipped on non-runnable host (device run evidence in W3/G2)"
            )
