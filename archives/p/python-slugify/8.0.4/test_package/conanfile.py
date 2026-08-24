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
        pkg = self.dependencies["python-slugify"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        # slugify 在模块加载时 import text_unidecode（同 aiosignal→frozenlist
        # / yarl→idna 先例）——把依赖包的 site-packages 一并加入 PYTHONPATH
        paths = [site]
        if "text-unidecode" in self.dependencies:
            paths.append(os.path.join(
                self.dependencies["text-unidecode"].package_folder,
                "lib", "python3.12", "site-packages"))
        site_all = os.pathsep.join(paths)
        # L0c + R34 合规：独立测试源文件（test_slugify.py——真实调用
        # 被测库 API）+ self.run 执行；上游 test.py（82 用例）一并实测
        tp_dir = os.path.dirname(__file__)
        test_script = os.path.join(tp_dir, "test_slugify.py")
        upstream = os.path.join(tp_dir, "test.py")
        self.run(
            f"PYTHONPATH='{site_all}' python3 '{test_script}' '{site_all}'",
            env="conanrun")
        if os.path.exists(upstream):
            self.run(
                f"PYTHONPATH='{site_all}' python3 -m unittest "
                f"test -v", env="conanrun", cwd=tp_dir)
