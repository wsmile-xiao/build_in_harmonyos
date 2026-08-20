import os
from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        bash = os.environ.get("CONFIG_SHELL", "bash")
        # 消费测试：test_alien.sh（L0c 测试源——alien --version/--help 运行——
        # perl -I 包/lib——Alien/Package/*.pm 找到；env_info.PERL5LIB 在
        # conan 2 的 conanrun 不注入——脚本内显式 -I 包/lib）
        self.run(f"{bash} test_alien.sh {pkg}", env="conanrun")
