#!/usr/bin/env python3
"""Conan test_package — oomd 0.5.0 消费者测试（真实执行打包产物）。

R34：设备与 CI worker 均不是 oomd 的合法运行环境（无 cgroup2 挂载点、
非 root），故按 wmname 0.1 先例断言上游确定性契约：
  - oomd --help 退出码恰为 0，且输出含 usage 行与 --cgroup-fs 选项
  - ELF 头：ELF64 / 小端 / AArch64
  - 真实链接 jsoncpp（DT_NEEDED 含 libjsoncpp）
详见 test.sh 内逐条注释。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class OomdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        bin_path = None
        pkg_folder = None
        for dep in self.dependencies.host.values():
            if dep.ref.name == "oomd":
                bindirs = dep.cpp_info.bindirs or ["bin"]
                bindir = bindirs[0]
                if not os.path.isabs(bindir):
                    bindir = os.path.join(dep.package_folder, bindir)
                bin_path = os.path.join(bindir, "oomd")
                pkg_folder = dep.package_folder
        if not bin_path or not os.path.isfile(bin_path):
            raise Exception("oomd binary not found in package bindirs")

        script = os.path.join(self.source_folder, "test.sh")
        if not os.path.isfile(script):
            raise Exception("test.sh missing in test_package")
        os.chmod(script, 0o755)

        # OHOS 默认 sh 不保证能 exec ELF，统一用 bash 承载被测二进制执行
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash):
            raise Exception(f"bash not found: {bash}")
        self.run(f"{bash} {script} {pkg_folder}", env="conanrun")
