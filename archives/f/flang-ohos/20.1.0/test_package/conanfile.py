import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "arch"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：跳过运行")
            return
        pkg = self.dependencies.build["flang-ohos"].package_folder
        flang = os.path.join(pkg, "bin", "flang")
        # R34 反空壳：真跑 flang 编译一段 Fortran，证明编译器可用（非仅存在）。
        src = os.path.join(self.source_folder, "hello.f90")
        self.run('{f} --version'.format(f=flang), env="conanbuild")
        self.run('{f} -c "{s}" -o hello.o'.format(f=flang, s=src), env="conanbuild")
        self.output.info("flang 编译 hello.f90 成功")
