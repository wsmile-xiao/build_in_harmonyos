import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 用源码根 Makefile 风格直接编译 test_package.cpp，避免引入 cmake 依赖
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        dep = self.dependencies["jpeg-compressor"]
        include_dir = os.path.join(dep.package_folder, "include")
        lib_dir = os.path.join(dep.package_folder, "lib")
        out = os.path.join(self.build_folder, "test_package")
        self.run(
            f"{cxx} -std=c++17 -O2 "
            f"-I{include_dir} "
            f"{os.path.join(self.source_folder, 'test_package.cpp')} "
            f"-L{lib_dir} -ljpeg_compressor -o {out}"
        )

    def test(self):
        exe = os.path.join(self.build_folder, "test_package")
        self.run(exe, env="conanrun")