#!/usr/bin/env python3
"""Conan recipe for packmol 21.2.3 on HarmonyOS PC (Fortran, Makefile).

packmol 是纯 Fortran 命令行工具：上游构建系统为手写 configure(仅探测编译器)
+ Makefile，无 Autotools、无外部库依赖（内嵌 GENCAN 优化器）。
本配方的 HarmonyOS 适配要点（根因见下）：

1. 编译：`tool_requires("flang-ohos/20.1.0")` 提供 LLVM Flang 前端，
   按扩展名自动选择自由/固定格式（src 混有 .f90 与 F77 的 .f）。
2. 链接：flang-ohos 是前端工具包，不含 OHOS CRT / sysroot / libc / libunwind；
   最终链接必须交由平台 clang 驱动并提供静态 Fortran 运行时
   （与 fortran-shlex/2.0.1 同款方案）。因此 patch 0001 把 Makefile 最终
   链接行从 $(FORTRAN) 分离为 $(LINKER) ... $(LIBS)（默认仍 = FORTRAN，
   不改动上游语义）。
3. flags：上游默认 `-march=native`，在受控 CI 上不可复现，配方固定为
   `-march=armv8-a`（与 profile arch=armv8 一致）。
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class PackmolConan(ConanFile):
    name = "packmol"
    version = "21.2.3"
    description = (
        "Molecular dynamics initial configuration builder: pack molecules "
        "into defined regions (spheres/boxes/polyhedra) and emit PDB/XYZ "
        "coordinate files"
    )
    license = "MIT"
    homepage = "https://m3g.github.io/packmol/"
    url = "https://github.com/m3g/packmol"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "packmol/21.2.3 is validated only for native HarmonyOS PC "
                "(os=OHOS, arch=armv8)"
            )

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # tool_requires 的 runenv（flang 运行时 libLLVM/libMLIR/libclang-cpp 的
        # LD_LIBRARY_PATH）由 VirtualBuildEnv 收集到 conanbuild 环境。
        VirtualBuildEnv(self).generate()

    def _build_tools(self):
        """定位 Flang 前端、OHOS clang 驱动与 Fortran 静态运行时。"""
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        flang = os.path.join(flang_pkg, "bin", "flang")
        fortran_runtime = os.path.join(flang_pkg, "lib", "libFortranRuntime.a")
        fortran_decimal = os.path.join(flang_pkg, "lib", "libFortranDecimal.a")

        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        clang = compilers.get("c", "/data/service/hnp/bin/clang")

        for tool in (flang, clang, fortran_runtime, fortran_decimal):
            if not os.path.isfile(tool):
                raise ConanInvalidConfiguration(
                    "required native HarmonyOS build tool is missing: {}".format(tool)
                )
        return flang, clang, fortran_runtime, fortran_decimal

    def build(self):
        apply_conandata_patches(self)
        flang, clang, fortran_runtime, _fortran_decimal = self._build_tools()
        src = self.source_folder

        if str(self.settings.build_type) == "Debug":
            flags = "-O0 -g"
        else:
            # 覆盖上游默认的 -march=native：保证受控 CI 上可复现。
            flags = "-O3 -funroll-loops -march=armv8-a"

        # 上游 Makefile all 目标：清理 .o/.mod → 编译全部源 → $(LINKER) 链接。
        #   FORTRAN=flang : LLVM Flang 前端
        #   LINKER=clang  : 提供平台 CRT/libc/libunwind/compiler-rt（flang-ohos 不含）
        #   LIBS          : 静态 Fortran 运行时（libFortranRuntime/libFortranDecimal）
        self.run(
            'make -C "{src}" FORTRAN="{fc}" FLAGS="{flags}" '
            'LINKER="{cc}" LIBS="-L{flib} -lFortranRuntime -lFortranDecimal -lm"'.format(
                src=src,
                fc=flang,
                flags=flags,
                cc=clang,
                flib=os.path.dirname(fortran_runtime),
            ),
            env="conanbuild",
        )
        if not os.path.isfile(os.path.join(src, "packmol")):
            raise ConanInvalidConfiguration("packmol binary was not produced")

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "packmol",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )

    def package_info(self):
        # 命令行工具，无链接接口需求
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]