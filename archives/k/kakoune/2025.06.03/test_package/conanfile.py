"""Conan test_package — 验证 kakoune 二进制可执行"""
from conan import ConanFile


class KakouneTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 验证 kak 二进制存在且可执行
        ret = self.run("kak -version", env="conanrun")
        if ret != 0:
            raise Exception("kak -version failed")
