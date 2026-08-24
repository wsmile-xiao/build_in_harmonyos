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
        pkg = self.dependencies["awl"].package_folder
        php_pkg = self.dependencies["php"].package_folder
        php_bin = os.path.join(php_pkg, "bin", "php")
        awl_inc = os.path.join(pkg, "include")
        # L0c + R34 合规：独立测试源文件（test_awl.py——真实调用被测库
        # API）+ self.run 执行
        test_script = os.path.join(os.path.dirname(__file__), "test_awl.py")
        self.run(f"python3 '{test_script}' '{php_bin}' '{awl_inc}'",
                 env="conanrun")
