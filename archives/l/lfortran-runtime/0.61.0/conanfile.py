#!/usr/bin/env python3
"""Conan recipe — lfortran-runtime 0.61.0 (纯 C 运行时库, HarmonyOS PC aarch64)

LFortran（LLVM 系现代 Fortran 编译器，https://github.com/lfortran/lfortran）随
编译器一同发布的 **C 运行时库** liblfortran_runtime：源码
src/libasr/runtime/lfortran_intrinsics.c，上游由 src/runtime/legacy/CMakeLists.txt
构建为 liblfortran_runtime.so（shared）与 liblfortran_runtime_static.a（static）。
LFortran 编译产物在链接期需要该运行时（约定函数名 _lfortran_* / _lcompilers_*，
如 _lfortran_dsin / _lfortran_sum / _lfortran_random / _lfortran_enable_fpe_traps），
本包单独提供该运行时库及其头文件。

构建策略（见 notes.md 实测证据）：
  上游顶层 CMake 工程强依赖 LLVM/MLIR 全量编译编译器主体，对"只交付运行时库"
  过重且不可行。实测确认该 C 运行时库可独立编译（仅额外需要 <libasr/config.h>，
  上游由顶层 CMake 的 configure_file(config.h.in) 生成，全特性关闭时内容即版本宏）。
  故本配方直接调用 OHOS SDK clang 编译单个源文件，产出与上游**同名**的
  liblfortran_runtime.so / liblfortran_runtime_static.a，并安装上游同路径头文件
  include/lfortran/impure/lfortran_intrinsics.h。

范围说明：上游 Fortran 侧运行时模块（src/runtime/{pure,impure,openmp}/
lfortran_intrinsic_*.f90）需 LFortran 编译器自举（上游 CMake 设
CMAKE_Fortran_COMPILER=lfortran），OHOS 无该编译器，故不在本包范围（见 notes.md）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, save)
from conan.tools.layout import basic_layout

# 上游 src/libasr/config.h 由顶层 CMake 的 configure_file(config.h.in) 生成；
# 关闭全部可选特性（LLVM/MLIR/stacktrace/assert/rapidjson 等）时的等价产物即下面内容。
# 运行时库本身不引用任何可选特性宏（仅条件包围 stacktrace 段），故只需版本宏。
CONFIG_H = """\
#ifndef LFORTRAN_CONFIG_H
#define LFORTRAN_CONFIG_H

#define LFORTRAN_VERSION "0.61.0"
#define LFORTRAN_MAJOR 0
#define LFORTRAN_MINOR 61
#define LFORTRAN_PATCHLEVEL 0

#endif // LFORTRAN_CONFIG_H
"""


class LFortranRuntimeConan(ConanFile):
    name = "lfortran-runtime"
    version = "0.61.0"
    description = "LFortran C runtime library (liblfortran_runtime) required by programs compiled with LFortran"
    license = "BSD-3-Clause"
    homepage = "https://lfortran.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "lfortran-runtime supports Linux/OHOS only, got %s" % self.settings.os)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 生成上游由 CMake configure_file 产出的 libasr/config.h（放入私有 include）
        inc = os.path.join(self.build_folder, "include", "libasr")
        os.makedirs(inc, exist_ok=True)
        save(self, os.path.join(inc, "config.h"), CONFIG_H)

    def _toolchain(self):
        # 编译器路径从 Conan 配置取（R33：禁止裸用 shell 变量 ${CC}）
        comp = self.conf.get("tools.build:compiler_executables",
                             check_type=dict, default={}) or {}
        cc = comp.get("c", "clang")
        ar = os.path.join(os.path.dirname(cc), "llvm-ar")
        if not os.path.exists(ar):
            ar = "llvm-ar"
        return cc, ar

    def build(self):
        apply_conandata_patches(self)
        cc, ar = self._toolchain()

        src_root = os.path.join(self.source_folder, "src")
        inc = os.path.join(self.build_folder, "include")
        csrc = os.path.join(src_root, "libasr", "runtime", "lfortran_intrinsics.c")
        bdir = os.path.join(self.build_folder, "build")
        os.makedirs(bdir, exist_ok=True)

        cflags = '-O2 -fPIC -I"{}" -I"{}"'.format(src_root, inc)
        if self.options.shared:
            out = os.path.join(bdir, "liblfortran_runtime.so.0.61.0")
            self.run('{} {} -shared -Wl,-soname,liblfortran_runtime.so.0 "{}" -o "{}" -lm'
                     .format(cc, cflags, csrc, out))
        else:
            obj = os.path.join(bdir, "lfortran_intrinsics.o")
            self.run('{} {} -c "{}" -o "{}"'.format(cc, cflags, csrc, obj))
            self.run('{} rcs "{}" "{}"'.format(
                ar, os.path.join(bdir, "liblfortran_runtime_static.a"), obj))

    def package(self):
        bdir = os.path.join(self.build_folder, "build")
        libd = os.path.join(self.package_folder, "lib")
        os.makedirs(libd, exist_ok=True)

        if self.options.shared:
            real = "liblfortran_runtime.so.0.61.0"
            copy(self, real, src=bdir, dst=libd)
            # 上游 CMake VERSION 0.61.0 / SOVERSION 0 → 生成 .so.0 与 .so 主名软链
            for name in ("liblfortran_runtime.so.0", "liblfortran_runtime.so"):
                link = os.path.join(libd, name)
                if os.path.lexists(link):
                    os.remove(link)
                os.symlink(real, link)
        else:
            copy(self, "liblfortran_runtime_static.a", src=bdir, dst=libd)

        # 头文件（上游安装路径：include/lfortran/impure/）
        copy(self, "lfortran_intrinsics.h",
             src=os.path.join(self.source_folder, "src", "libasr", "runtime"),
             dst=os.path.join(self.package_folder, "include", "lfortran", "impure"))
        # 许可证
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 上游命名：shared = lfortran_runtime，static = lfortran_runtime_static
        self.cpp_info.libs = ["lfortran_runtime"] if self.options.shared \
            else ["lfortran_runtime_static"]
        self.cpp_info.includedirs = ["include"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
