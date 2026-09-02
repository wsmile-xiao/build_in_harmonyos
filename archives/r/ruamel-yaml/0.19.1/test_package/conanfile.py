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
        pkg = self.dependencies["ruamel-yaml"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        # L0c + R34 合规：独立测试源文件（真实调用被测库 API）+ self.run
        # 执行——冒烟测试 + 鸿蒙特有测试（平台导入/注释 roundtrip/
        # Unicode+CRLF/真文件 IO）
        for name in ("test_ruamel_yaml.py", "test_ohos_compat.py"):
            test_script = os.path.join(os.path.dirname(__file__), name)
            self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
