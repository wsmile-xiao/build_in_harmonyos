"""Conan test_package — libsgp4/1.0 consumer test (C++).

Compiles a real consumer against the packaged static archive and runs it.
The probe exercises TLE parsing, SGP4 propagation against values from an
independent SGP4 implementation, error signalling and the look-angle API.
See test.cpp for the assertion list and reports/test-report.md for counts.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class Libsgp4TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libsgp4"].cpp_info
        incs = ["-I" + p for _ref, d in self.dependencies.items()
                for p in d.cpp_info.includedirs]
        libdirs = [p for _ref, d in self.dependencies.items() for p in d.cpp_info.libdirs]
        link = ["-L" + p for p in libdirs] + ["-l" + lib for lib in dep.libs]
        cxx = os.environ.get("CXX", "clang++")
        # 库本体按 profile 的 cppstd 编，测试标准必须跟上。
        std = self.settings.get_safe("compiler.cppstd")
        std_flag = ("-std=c++%s" % str(std).replace("gnu", "")) if std else ""
        src = os.path.join(self.source_folder, "test.cpp")
        out = os.path.join(self.build_folder, "test_probe")
        self.run(" ".join([cxx, std_flag, '"%s"' % src, "-o", '"%s"' % out] + incs + link))

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: consumer probe not executed")
            return
        probe = os.path.join(self.build_folder, "test_probe")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run('"%s" -c "%s"' % (bash, probe), env="conanrun")
