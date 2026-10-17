import os

from conan import ConanFile


class DictionTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["diction"].package_folder
        # R34: 消费者测试真实执行随包安装的 diction 二进制，并依赖随包安装的
        # 短语库（默认查找路径，不传 -f/-n）。
        self.run(f"sh test_diction.sh {pkg_folder}", env="conanrun")
        self.output.info("diction: OK")
