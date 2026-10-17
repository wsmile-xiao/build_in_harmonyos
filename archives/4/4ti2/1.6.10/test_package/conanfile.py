#!/usr/bin/env python3
"""4ti2 test_package — qsolve C API 与 gensymm CLI 验证"""
import os
import tempfile
from conan import ConanFile


class FourTi2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 直接编译+链接（非 dlopen）：既 #include 公共头（4ti2 include/，含 gmp
        # 传递头），又链接静态库（4ti2 lib/ + 传递 glpk/gmp lib）——CI 的 L1e
        # 会把 include/ 与 lib/ 移走再跑一次，两处都要真实依赖。
        incs, linkdirs, rpaths = [], [], []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            for p in _d.cpp_info.libdirs:
                if os.path.isdir(p):
                    linkdirs.append("-L" + p)
                    rpaths.append("-Wl,-rpath-link," + p)
        comp = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict)
        cc = comp.get("c", "/data/service/hnp/bin/clang")
        cxx = comp.get("cpp", "/data/service/hnp/bin/clang++")
        # 源码走 C 编译以验证 extern "C" 公共 API；链接用 clang++，
        # 因为 lib4ti2*.a 内含 C++ 代码，需要 libc++ 运行时。
        self.run(f'{cc} -c test.c -o test.o {" ".join(incs)}')
        self.run(f'{cxx} test.o -o test_probe {" ".join(linkdirs)} {" ".join(rpaths)} '
                 f'-l4ti2int64 -l4ti2common -l4ti2util -lglpk -lgmp -lm')

    def test(self):
        # 1) C API 测试：qsolve 参考算例（对齐上游 test/qsolve/api/qsolve_main.cpp），
        #    校验计算出的 4x3 qhom 矩阵，非零退出码即失败。
        self.run("./test_probe", env="conanrun")
        # 2) CLI 二进制验证：执行包内 gensymm 工具（在 $TMPDIR 草稿目录中运行，
        #    避免其输出文件 333.sym 污染 test_package 源码树）。
        _pkg = self.dependencies["4ti2"].package_folder
        _gensymm = os.path.join(_pkg, "bin", "gensymm")
        _scratch = tempfile.mkdtemp(prefix="4ti2-gensymm-")
        self.run(f'cd "{_scratch}" && "{_gensymm}" 3 3 3 1 333', env="conanrun")
