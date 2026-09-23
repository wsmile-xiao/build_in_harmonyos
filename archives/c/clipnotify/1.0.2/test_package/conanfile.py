#!/usr/bin/env python3
"""Conan test_package — clipnotify 1.0.2 消费者测试.

R34: 实质执行打包产物。OHOS 设备无 X server，clipnotify 的确定性错误
路径即最小充分断言：已签名 ELF 可执行（XPM 白名单）+ 动态链接 X11
正确解析（conanrun 提供 LD_LIBRARY_PATH）+ exit 1 + "Can't open X display"。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class ClipnotifyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        pkg_bin = None
        for dep in self.dependencies.host.values():
            if dep.ref.name == "clipnotify":
                bindirs = dep.cpp_info.bindirs or ["bin"]
                bindir = bindirs[0]
                if not os.path.isabs(bindir):
                    bindir = os.path.join(dep.package_folder, bindir)
                pkg_bin = os.path.join(bindir, "clipnotify")
        if not pkg_bin or not os.path.isfile(pkg_bin):
            raise Exception("clipnotify binary not found in package bindirs")

        script = os.path.join(self.source_folder, "test_nox.sh")
        if not os.path.isfile(script):
            raise Exception("test_nox.sh missing in test_package")
        os.chmod(script, 0o755)
        out_file = os.path.join(self.build_folder, "clipnotify_out.txt")
        # L0c: 测试逻辑落在 test_nox.sh（测试源文件），此处实质调用
        self.run(f'"{script}" "{pkg_bin}" "{out_file}"', env="conanrun")
        self.output.info("clipnotify consumer test PASSED (signed ELF runs, no-X error path verified)")
