"""test_package/conanfile.py — kconfiglib 消费者测试驱动。

沿用本仓库纯 Python 包（wcwidth / ptyprocess）的范式：
把被测包解开后的 site-packages 目录塞进 PYTHONPATH，
再以子进程运行消费者断言脚本。
"""
from conan import ConanFile
import os
import sys


class KconfiglibTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        site_packages = os.path.join(
            package, "lib",
            "python{}.{}".format(sys.version_info.major, sys.version_info.minor),
            "site-packages",
        )
        script = os.path.join(self.recipe_folder, "test_kconfiglib.py")

        old = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = site_packages + (
            os.pathsep + old if old else ""
        )
        # ⚠ PYTHONDONTWRITEBYTECODE：消费者测试导入被测包时，Python 会在
        #   包目录里写 __pycache__/*.pyc。那属于构建产物，且发生在 package()
        #   之后（package() 里的清理拦不住），会被 Conan 一并收进制品。
        #   在源头禁掉最干净。
        old_dwb = os.environ.get("PYTHONDONTWRITEBYTECODE")
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            self.run('"{}" "{}"'.format(sys.executable, script))
        finally:
            if old is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = old
            if old_dwb is None:
                os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
            else:
                os.environ["PYTHONDONTWRITEBYTECODE"] = old_dwb
