import os
from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        # L0d 要求 test() 必须 self.run（不能只是 assert——L0 门禁实测失败）
        # ——测试源 test_asql.sh（打包完整性检查 + perl 语法）
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test_asql.sh {pkg}", env="conanrun")
