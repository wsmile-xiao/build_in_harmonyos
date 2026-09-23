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
        pkg = self.dependencies["bacula-client"].package_folder
        # L0c 合规：独立测试源文件 + self.run 执行
        test = os.path.join(os.path.dirname(__file__),
                            "test_bacula_client.py")
        self.run(f"python3 '{test}' '{pkg}'", env="conanrun")
