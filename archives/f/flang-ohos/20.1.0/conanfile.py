#!/usr/bin/env python3
"""Conan recipe — flang-ohos 20.1.0 (cmake, 鸿蒙 PC 真机原生编译)

LLVM Flang（Fortran 前端）工具链，作 tool 包供含 Fortran 的库（openblas/scipy 等）在设备上
`conan create` 时 tool_requires。设备/NDK 不带 Fortran 编译器，本包补齐。

⚠️ 本地打包例外（同 llvm/20.1.0）：从源码全量编 LLVM+MLIR+Clang+Flang 真机约 73 分钟，**超 CI 硬超时
   45 分钟**，CI 必 fail、产不出二进制。二进制由「真机编好 → conan cache save → 手动 conan upload」提供
   （已上传 openharmonypcdeveloper-conan）。本 recipe 仅留档 + 可复现构建方法。
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get


class FlangOhosConan(ConanFile):
    name = "flang-ohos"
    version = "20.1.0"
    description = "LLVM Flang（Fortran 前端）工具链，AArch64，供含 Fortran 的库设备原生编译时 tool_requires"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://flang.llvm.org"
    package_type = "application"
    settings = "os", "arch"

    def source(self):
        # 归档为 llvm-project-20.1.0.src/{llvm,clang,mlir,flang,...}；strip_root 后直含 llvm/ 子目录。
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 真机原生（aarch64→aarch64）：不设 CMAKE_SYSTEM_NAME，裸 cmake + 设备 hnp clang（同 llvm recipe）。
        src = os.path.join(self.source_folder, "llvm")
        bdir = os.path.join(self.build_folder, "build-ohos")
        # config.guess stub + Platform/HarmonyOS.cmake（设备 uname=HarmonyOS，cmake 不认；见 llvm recipe 注释）
        with open(os.path.join(src, "cmake", "config.guess"), "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\necho aarch64-unknown-linux-ohos\n")
        pm = os.path.join(self.build_folder, "_cmake_modules")
        os.makedirs(os.path.join(pm, "Platform"), exist_ok=True)
        with open(os.path.join(pm, "Platform", "HarmonyOS.cmake"), "w", encoding="utf-8") as f:
            f.write("include(Platform/Linux)\n")
        cc = "/data/service/hnp/bin/clang"
        cxx = "/data/service/hnp/bin/clang++"
        defs = " ".join([
            "-G Ninja",
            '-DCMAKE_MODULE_PATH="{}"'.format(pm),
            '-DCMAKE_C_COMPILER="{}"'.format(cc),
            '-DCMAKE_CXX_COMPILER="{}"'.format(cxx),
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_INSTALL_LIBDIR=lib",
            # flang 需 mlir + clangDriver；出聚合 dylib 大幅瘦身（消费仅需 flang 前端）
            '-DLLVM_ENABLE_PROJECTS="mlir;clang;flang"',
            "-DLLVM_BUILD_LLVM_DYLIB=ON",
            "-DLLVM_LINK_LLVM_DYLIB=ON",
            "-DLLVM_ENABLE_PIC=ON",
            "-DLLVM_ENABLE_RTTI=ON",
            "-DLLVM_TARGETS_TO_BUILD=AArch64",
            "-DLLVM_HOST_TRIPLE=aarch64-unknown-linux-ohos",
            "-DLLVM_DEFAULT_TARGET_TRIPLE=aarch64-unknown-linux-ohos",
            "-DLLVM_ENABLE_ASSERTIONS=OFF",
            "-DLLVM_INCLUDE_EXAMPLES=OFF",
            "-DLLVM_INCLUDE_TESTS=OFF",
            "-DLLVM_INCLUDE_BENCHMARKS=OFF",
            "-DLLVM_INCLUDE_DOCS=OFF",
            "-DCLANG_INCLUDE_TESTS=OFF",
            "-DFLANG_INCLUDE_TESTS=OFF",
            "-DMLIR_INCLUDE_TESTS=OFF",
            "-DLLVM_ENABLE_ZLIB=OFF",
            "-DLLVM_ENABLE_ZSTD=OFF",
            "-DLLVM_ENABLE_LIBXML2=OFF",
            "-DLLVM_ENABLE_TERMINFO=OFF",
            "-DLLVM_ENABLE_LIBEDIT=OFF",
            "-DLLVM_ENABLE_LIBPFM=OFF",
            "-DLLVM_PARALLEL_LINK_JOBS=2",
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, defs))
        # 目标化编译：flang 编译器 + Fortran 运行时（20.1.0 运行时是 in-tree flang/runtime，
        # 目标 FortranRuntime/FortranDecimal；内建 .mod 随之生成到 build/include/flang）。省去无关工具。
        self.run('cmake --build "{}" -j12 --target flang FortranRuntime FortranDecimal'.format(bdir))

    def package(self):
        # 只打最小运行集（bin/flang + 依赖 .so + Fortran 运行时 .a + 内建模块），不 cmake --install（会装全量）。
        bdir = os.path.join(self.build_folder, "build-ohos")
        pf = self.package_folder
        for d in ("bin", "lib", os.path.join("include", "flang")):
            os.makedirs(os.path.join(pf, d), exist_ok=True)
        # 编译器（实体 flang-20 + flang/flang-new 软链）
        for name in ("flang-20", "flang", "flang-new"):
            s = os.path.join(bdir, "bin", name)
            if os.path.exists(s) or os.path.islink(s):
                self.run('cp -P "{}" "{}"'.format(s, os.path.join(pf, "bin", name)))
        # 运行所需 .so（flang NEEDED：libLLVM/libMLIR/libclang-cpp）+ 主名软链
        for so in glob.glob(os.path.join(bdir, "lib", "lib*.so*")):
            base = os.path.basename(so)
            if base.startswith(("libLLVM.so", "libMLIR.so", "libclang-cpp.so")):
                self.run('cp -P "{}" "{}"'.format(so, os.path.join(pf, "lib", base)))
        # 链接 Fortran 用的运行时静态库
        for a in ("libFortranRuntime.a", "libFortranDecimal.a", "libFortranCommon.a"):
            s = os.path.join(bdir, "lib", a)
            if os.path.isfile(s):
                self.run('cp "{}" "{}"'.format(s, os.path.join(pf, "lib", a)))
        # 内建模块
        for mod in glob.glob(os.path.join(bdir, "include", "flang", "*.mod")):
            self.run('cp "{}" "{}"'.format(mod, os.path.join(pf, "include", "flang", os.path.basename(mod))))
        self._sign()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign(self):
        # XPM：dlopen 的 .so 与被 exec 的 flang 都要自签。
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        targets = glob.glob(os.path.join(self.package_folder, "lib", "*.so*"))
        bindir = os.path.join(self.package_folder, "bin")
        for name in os.listdir(bindir) if os.path.isdir(bindir) else []:
            p = os.path.join(bindir, name)
            if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                targets.append(p)
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.buildenv_info.define_path("FC", os.path.join(self.package_folder, "bin", "flang"))
        self.buildenv_info.define_path("FLANG_RT_LIB",
                                       os.path.join(self.package_folder, "lib", "libFortranRuntime.a"))
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        # 消费方运行 flang 时需 lib/ 上 LD_LIBRARY_PATH（libLLVM/libMLIR/libclang-cpp）
        self.runenv_info.append_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        self.buildenv_info.append_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
