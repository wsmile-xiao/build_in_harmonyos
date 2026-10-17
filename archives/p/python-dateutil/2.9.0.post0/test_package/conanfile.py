from conan import ConanFile
from conan.tools.build import can_run
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["python-dateutil"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        # dateutil 在模块加载时 import six（依赖包）——把 six 的
        # site-packages 一并加入 PYTHONPATH（同 slugify→text-unidecode
        # 先例）
        paths = [site]
        if "six" in self.dependencies:
            paths.append(os.path.join(
                self.dependencies["six"].package_folder,
                "lib", "python3.12", "site-packages"))
        site_all = os.pathsep.join(paths)
        # L0c + R34 合规：独立测试源文件（test_dateutil.py——真实调用
        # 被测库 API）+ self.run 执行
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_dateutil.py")
        self.run(f"python3 '{test_script}' '{site_all}'", env="conanrun")
