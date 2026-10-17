import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        # gcobol 完整构建（--enable-languages=c,cobol）自动产出 libgcobol，
        # gcobol 驱动按 libgcobol.spec 自动链接，无需独立 libgcobol conan 包。
        self.requires(self.tested_reference_str)

    def build(self):
        # 编译在 test() 的 test.sh 里完成（gcobol 在 conanrun PATH 中）。
        pass

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译")
            return
        self.run("sh test.sh", env="conanrun")
