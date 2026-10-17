#!/usr/bin/env python3
"""Conan test_package for plyara 2.2.8 — consumer verification.

执行两个独立测试源文件（满足 L0c）：
  1. test_plyara.py      —— R34 消费者测试：从包内 site-packages 导入
                            plyara + 内嵌 PLY，走真实 parse API
  2. test_ohos_plyara.py —— 鸿蒙专项测试：OHOS 平台身份 / submodule 交付形态 /
                            只读工作目录与只读临时目录契约 / CLI 端到端哈希
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class PlyaraTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["plyara"].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isdir(site):
            raise ConanException(f"site-packages missing: {site}")
        # 交付形态守护：两个模块与 CLI 入口都必须存在
        for mod in ("plyara", "ply"):
            if not os.path.isfile(os.path.join(site, mod, "__init__.py")):
                raise ConanException(f"{mod}/ missing under {site}")
        cli = os.path.join(pkg, "bin", "plyara")
        if not os.path.isfile(cli):
            raise ConanException(f"bin/plyara missing: {cli}")

        # 沙箱 PATH 无 python3 的教训（packaging 2.6 / appdirs）——用绝对路径
        py = sys.executable if os.path.isfile(sys.executable or "") else "python3"
        here = os.path.dirname(os.path.abspath(__file__))
        for script in ("test_plyara.py", "test_ohos_plyara.py"):
            path = os.path.join(here, script)
            if not os.path.isfile(path):
                raise ConanException(f"{script} missing: {path}")
            self.run(f"'{py}' '{path}' '{pkg}' '{site}'", env="conanrun")
