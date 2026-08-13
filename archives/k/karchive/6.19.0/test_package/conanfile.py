#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class KArchiveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _deps_flags(self, dep):
        """收集依赖包的 include/lib flags（karchive + qtbase）"""
        inc = " ".join(f"-I{os.path.join(dep.package_folder, d)}" for d in dep.cpp_info.includedirs)
        lib = " ".join(f"-L{os.path.join(dep.package_folder, d)}" for d in dep.cpp_info.libdirs)
        return inc, lib

    def test(self):
        # 编译并运行 test_karchive.cpp：调用 KCompressionDevice API，验证库
        # 可实际编译链接运行（非空壳测试，R34）。$CXX/$CXXFLAGS 来自
        # VirtualBuildEnv（env="conanbuild" 激活）
        karchive = self.dependencies["karchive"]
        qtbase = self.dependencies["qtbase"]
        kinc, klib = self._deps_flags(karchive)
        qinc, qlib = self._deps_flags(qtbase)
        # Qt6 头文件在 include/QtCore 子目录（QBuffer 等），cpp_info.includedirs
        # 仅含 include 顶层，补 -I QtCore 路径（否则 #include <QBuffer> 找不到）
        qinc += f" -I{os.path.join(qtbase.package_folder, 'include', 'QtCore')}"
        # karchive 头文件在 include/KF6/KArchive 子目录（kcompressiondevice.h
        # 等），cpp_info.includedirs 仅含 include 顶层，补 -I KF6/KArchive 路径
        kinc += f" -I{os.path.join(karchive.package_folder, 'include', 'KF6', 'KArchive')}"
        src = os.path.join(self.source_folder, "src", "test_karchive.cpp")
        test_bin = os.path.join(self.build_folder, "test_karchive")
        # -std=c++17：Qt6 头文件硬性要求 C++17（qcompilerdetection.h:
        # "Qt requires a C++17 compiler"），CXXFLAGS 未含则编译失败
        # libKF6Archive.a 静态库依赖 zstd（kzstdfilter）+ zlib（kgzipfilter），
        # 链接需显式 -lzstd -lz（cattle -lffi 同类问题——静态库依赖传递）
        zstd_lib = os.path.join(self.dependencies["zstd"].package_folder, "lib")
        zlib_lib = os.path.join(self.dependencies["zlib"].package_folder, "lib")
        ret = self.run(
            f'${{CXX:-clang++}} ${{CXXFLAGS}} -std=c++17 -o "{test_bin}" "{src}" '
            f"{kinc} {qinc} {klib} {qlib} -L{zstd_lib} -L{zlib_lib} "
            f"-lKF6Archive -lQt6Core -lzstd -lz",
            env="conanbuild",
        )
        if ret != 0:
            raise ConanException(f"test_karchive.cpp compilation failed with exit code {ret}")

        if can_run(self):
            ret = self.run(f'"{test_bin}"', env="conanrun")
            if ret != 0:
                raise ConanException(f"test_karchive run failed with exit code {ret}")
            self.output.info("karchive API verified successfully")
        else:
            self.output.info("Cross-building: test compiled, verification skipped")