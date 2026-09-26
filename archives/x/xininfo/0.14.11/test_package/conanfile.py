#!/usr/bin/env python3
"""Conan test_package — xininfo 0.14.11 消费者测试.

R34：实质执行打包产物。OHOS 设备/CI 无 X server（2026-09-25 B 机实测
DISPLAY 为空，Xvfb/Xephyr/Xwayland/man 均 MISSING），故断言面取
"可执行 + 链接 + 代码路径可达 + 产物完整"四类确定性断言，与同仓
clipnotify/1.0.2（test_nox.sh）、xsel/1.2.1（test_xsel.sh）同口径；
不发明新的降级形态。

所有测试输出写到进程私有目录 $OUT（conanfile 传入），正反两轮（L1e
破坏性反向验证会对同一 test_package 起第二次 conan test）不复用同一份
文件，避免负照轮把参考输出覆写掉。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class XininfoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        pkg_folder = None
        for dep in self.dependencies.host.values():
            if dep.ref.name == "xininfo":
                pkg_folder = dep.package_folder
        if not pkg_folder or not os.path.isdir(pkg_folder):
            raise Exception("xininfo package folder not found (R34)")

        bindir = os.path.join(pkg_folder, "bin")
        binary = os.path.join(bindir, "xininfo")
        if not os.path.isfile(binary):
            raise Exception(f"xininfo binary not found in package bindirs: {binary}")

        script = os.path.join(self.source_folder, "test_xininfo.sh")
        if not os.path.isfile(script):
            raise Exception("test_xininfo.sh missing in test_package")
        os.chmod(script, 0o755)

        out_dir = os.path.join(self.build_folder, f"xininfo-test-out-{os.getpid()}")
        # OHOS: /system/bin/sh (mksh) 执行 ELF 不可靠，用 bash 包装（xsel 同法）
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        self.run(f'"{bash}" "{script}" "{binary}" "{bindir}" "{pkg_folder}" "{out_dir}"',
                 env="conanrun")
        self.output.info("xininfo consumer test finished (see assertions above)")
