#!/usr/bin/env python3
"""Conan test_package — rampler 2.1.1 消费者测试.

R34: 实质执行打包产物。
  ① `rampler -v` → 断言输出含版本串 "2.1.1"（已签名 ELF 可执行 + 动态依赖解析）；
  ② 无参数 → 断言 `[rampler::] error: missing arguments!`（main.cpp 确定性早退路径）。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class RamplerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        pkg_bin = None
        for dep in self.dependencies.host.values():
            if dep.ref.name == "rampler":
                bindir = (dep.cpp_info.bindirs or ["bin"])[0]
                if not os.path.isabs(bindir):
                    bindir = os.path.join(dep.package_folder, bindir)
                pkg_bin = os.path.join(bindir, "rampler")
        if not pkg_bin or not os.path.isfile(pkg_bin):
            raise Exception("rampler not found in package bindirs")

        script = os.path.join(self.source_folder, "test_rampler.sh")
        if not os.path.isfile(script):
            raise Exception("test_rampler.sh missing in test_package")
        os.chmod(script, 0o755)
        out_file = os.path.join(self.build_folder, "rampler_out.txt")
        self.run(f'sh "{script}" "{pkg_bin}" "{out_file}"', env="conanrun")
        self.output.info("rampler consumer test PASSED (version + missing-args paths)")
