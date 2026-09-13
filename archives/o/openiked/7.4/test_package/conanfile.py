#!/usr/bin/env python3
"""Conan test_package — openiked 7.4 消费者测试.

R34: 实质执行打包产物。iked 是需要 root/pfkey 的 VPN 守护进程（平台
限制：不做 IPsec 数据面端到端），最小充分断言为：
  1. `iked -V` 打印 "OpenIKED" 版本横幅且 rc=0（证明 ELF 可执行 +
     crypto/event 链接正确解析）
  2. `ikectl` 无参调用打印 usage 且 rc 非 0（工具控制面可执行）
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class OpenikedTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        pkg_bin = None
        for dep in self.dependencies.host.values():
            if dep.ref.name == "openiked":
                bindirs = dep.cpp_info.bindirs or ["bin"]
                bindir = bindirs[0]
                if not os.path.isabs(bindir):
                    bindir = os.path.join(dep.package_folder, bindir)
                pkg_bin = os.path.join(bindir)
        if not pkg_bin or not os.path.isdir(pkg_bin):
            raise Exception("openiked bin dir not found in package")
        script = os.path.join(self.source_folder, "test_basic.sh")
        if not os.path.isfile(script):
            raise Exception("test_basic.sh missing in test_package")
        os.chmod(script, 0o755)
        self.run(f'"{script}" "{pkg_bin}"', env="conanrun")
        self.output.info("openiked consumer test PASSED (iked -V banner + ikectl usage verified)")
