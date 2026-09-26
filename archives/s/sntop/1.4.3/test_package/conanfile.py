import os

from conan import ConanFile


class TestSntopConan(ConanFile):
    """sntop 是 CLI/curses 应用，交付物只有可执行文件，因此消费者测试的做法是
    "编译一个真实的使用者程序，由它去驱动被测二进制并断言其行为"。
    被测行为与断言清单见同目录 src/test_sntop.c 顶部注释。
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = executables.get("c") or "clang"
        src = os.path.join(self.source_folder, "src", "test_sntop.c")
        out = os.path.join(self.build_folder, "test_sntop")
        self.run('"{cc}" -o "{out}" "{src}"'.format(cc=cc, out=out, src=src),
                 env="conanbuild")

    def test(self):
        pkg = self.dependencies["sntop"].package_folder
        sntop_bin = os.path.join(pkg, "bin", "sntop")
        test_bin = os.path.join(self.build_folder, "test_sntop")
        # 工作目录给绝对路径并预先建好：被测程序把 HTML 报表写到 -e 指定处，
        # 相对 cwd 写会在框架的第二次 conan test（负照轮）里被复用/覆写。
        work = os.path.join(self.build_folder, "sntop-consumer-work")
        os.makedirs(work, exist_ok=True)
        self.run('"{tb}" "{bin}" "{work}"'.format(tb=test_bin, bin=sntop_bin,
                                                  work=work),
                 env="conanrun")
