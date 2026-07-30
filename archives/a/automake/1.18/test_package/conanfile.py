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
        self.run("aclocal --version", env="conanbuild")
        self.output.info("[ok] aclocal 可执行")
        self.run("automake --version", env="conanbuild")
        self.output.info("[ok] automake 可执行")
        # ACLOCAL_PATH 是否真的接上：列一下能看到的宏目录
        self.run("echo ACLOCAL_PATH=$ACLOCAL_PATH", env="conanbuild")
        self.run("echo PERL5LIB=$PERL5LIB", env="conanbuild")
        # 真正的验收：让 aclocal 在一个最小 configure.ac 上跑一遍并产出 aclocal.m4
        import textwrap
        with open("configure.ac", "w", encoding="utf-8") as f:
            f.write(textwrap.dedent("""\
                AC_INIT([probe],[0.1])
                AM_INIT_AUTOMAKE
                AC_OUTPUT
                """))
        self.run("aclocal", env="conanbuild")
        if not os.path.isfile("aclocal.m4"):
            raise Exception("aclocal 没产出 aclocal.m4 —— 宏路径没接对")
        self.output.info("[ok] aclocal 在真实 configure.ac 上产出了 aclocal.m4")
