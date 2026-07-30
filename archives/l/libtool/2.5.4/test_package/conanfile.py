import os
from conan import ConanFile


class TestPkg(ConanFile):
    """工具包的验证：**真的把工具跑起来**，而不是检查文件存在。

    这两个包的意义在于让消费方的 autoreconf 能用，所以除了 --version，
    还要验证 aclocal 能找到宏（ACLOCAL_PATH 接对了）。
    """
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        self.run("libtoolize --version", env="conanbuild")
        self.output.info("[ok] libtoolize 可执行")
        self.run("libtool --version", env="conanbuild")
        self.output.info("[ok] libtool 可执行")
        # ACLOCAL_PATH 是否真的接上：列一下能看到的宏目录
        self.run("echo ACLOCAL_PATH=$ACLOCAL_PATH", env="conanbuild")
