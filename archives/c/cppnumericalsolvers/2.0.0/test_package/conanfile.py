import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 消费者依赖链同库要求：eigen 头文件（library 公开 API 依赖）
        self.requires("eigen/3.4.1")

    def build(self):
        # R33: 编译器从 Conan conf 取，不裸用 ${CC}/${CXX}
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        dep = self.dependencies["cppnumericalsolvers"].cpp_info
        eigen_inc = " ".join("-I" + p for p in self.dependencies["eigen"].cpp_info.includedirs)
        inc = " ".join("-I" + p for p in dep.includedirs)
        # 消费者编译：仅公开头文件 include/cppoptlib，链接无 .so/.a（header-only）
        self.run(
            f"{cxx} -std=c++17 -O1 {inc} {eigen_inc} test_cppoptlib.cpp "
            f"-o test_cppoptlib",
            cwd=self.build_folder,
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译")
            return
        # 消费者运行：调用公开 API L-BFGS 求解 Rosenbrock，断言可观察结果
        self.run("./test_cppoptlib", env="conanrun")