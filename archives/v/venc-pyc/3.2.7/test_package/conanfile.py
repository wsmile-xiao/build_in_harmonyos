#!/usr/bin/env python3
"""Conan test_package — venc-pyc 3.2.7 消费者验证。

test() 内断言（L0d 要求 test() 必须调用 self.run）：
  1. python3 smoke.py：import venc3 / .pyc 存在 / .py 与 .pyc 并存 /
     pyc 直接加载 / package_data 资源完整
  2. bin/venc -v（CLI smoke，退出码 0）

PYTHONPATH 由 conanfile.py 的 package_info 注入；此处再显式 os.environ 注入
保证 smoke.py 与 CLI 均可解析 venc3 模块（conan 2.29 self.run 的 env
参数仅接受 list，故改用 os.environ 临时注入）。
"""
import os
import sys

from conan import ConanFile


class VencPycTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        site_packages = os.path.join(
            pkg, "lib",
            "python{}.{}".format(sys.version_info.major, sys.version_info.minor),
            "site-packages")
        cli = os.path.join(pkg, "bin", "venc")
        smoke = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke.py")

        # 运行时 Python 包依赖：smoke.py 断言 import venc3.datastore（顶层
        # import unidecode）且 venc CLI 运行依赖 yaml；干净 CI 环境无此二包，
        # 先安装（社区源有 cp312-ohos_aarch64 预编译 wheel，见 conanfile.py 注）。
        ret = self.run("python3 -m pip install unidecode pyyaml --quiet 2>&1")
        if ret != 0:
            raise Exception(f"pip install runtime deps failed with exit code {ret}")

        old_env = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = site_packages + (os.pathsep + old_env if old_env else "")
        try:
            # 1) 断言脚本（import / pyc 存在 / py 与 pyc 并存 / pyc 直接加载 /
            #    package_data 资源完整）
            ret = self.run("python3 {} 2>&1".format(smoke))
            if ret != 0:
                raise Exception(f"test_package smoke.py failed with exit code {ret}")
            # 2) CLI smoke（venc -v 版本命令，退出码 0）
            ret = self.run("{} -v >/dev/null 2>&1".format(cli))
            if ret != 0:
                raise Exception(f"venc -v failed with exit code {ret}")
        finally:
            if old_env is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = old_env
