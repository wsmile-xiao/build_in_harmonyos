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
        pkg = self.dependencies["cc"].package_folder
        inc = os.path.join(pkg, "include")
        # L0c 合规：独立测试源文件（test_cc.c = 上游 tests/unit_tests.c，
        # 2043 行多容器 C 单元测试）+ self.run 编译运行真实执行——
        # clang 绝对路径（conanrun PATH 不含，同 gbdk/simavr 教训）
        test_src = os.path.join(os.path.dirname(__file__), "test_cc.c")
        exe = os.path.join(os.path.dirname(__file__), "test_cc")
        self.run(
            f"/data/service/hnp/bin/clang '{test_src}' -I'{inc}' "
            f"-o '{exe}'",
            env="conanrun",
        )
        # 运行上游单元测试（exit 0 = 全部通过，输出 All done.）
        self.run(f"'{exe}'", env="conanrun")
