#!/usr/bin/env python3
"""test_package — 编译、链接并调用 libgslip 公开 API 的消费者测试."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class GslipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # R33：不裸用 shell 环境变量；经 Conan conf 获取 C++ 编译器
            cxx_map = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
            cxx = cxx_map.get("cpp") or str(self.settings.compiler)
            src = os.path.join(self.source_folder, "consumer.cpp")
            bin_path = os.path.join(self.build_folder, "gslip_consumer")
            pkg = self.dependencies["gslip"]
            inc_flags = " ".join(
                f"-I{os.path.join(pkg.package_folder, d)}"
                for d in pkg.cpp_info.includedirs
            )
            lib_flags = " ".join(
                f"-L{os.path.join(pkg.package_folder, d)}"
                for d in pkg.cpp_info.libdirs
            )
            self.run(
                f"{cxx} -o {bin_path} {src} {inc_flags} {lib_flags} -lgslip",
                env="conanbuild",
            )
            self.run(bin_path, env="conanrun")
