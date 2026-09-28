#!/usr/bin/env python3
"""Conan recipe — fixed_point_arith 0.0-git9b5da0fa97 (upstream plain Makefile, C library).

fixed_point_arith 官方源码为纯 Makefile 工程（无 configure、无 CMake、无 install 目标）：
  - make 产出静态库 build/fixed_point.a + .sym 符号表；
  - 无外部第三方依赖（仅依赖 libc 的 stdint/stdbool）；
  - 头文件位于 include/fixed_point/，公开 API 需定义 FXP_C99_INLINE 才声明
    （上游 Makefile 亦以 -DFXP_C99_INLINE 编译，README 默认用法一致）；
  - 配方以 OUT_DIR 指向 build_folder，避免污染源码目录（R49 私有前缀精神）；
  - make 恒用 -j1（R9，HMDFS jobserver fifo 限制）。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class FixedPointArithConan(ConanFile):
    name = "fixed_point_arith"
    version = "0.0-git9b5da0fa97"
    description = "Fixed point arithmetic routines in C (Q format), with vectors and quaternions"
    license = "BSD-3-Clause"
    homepage = "https://github.com/jcarrano/fixed_point_arith"
    url = ""  # CI fills this
    topics = ("fixed-point", "q-format", "vector", "quaternion")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = executables.get("c") or "clang"
        ar = executables.get("ar") or "llvm-ar"
        nm = executables.get("nm") or "llvm-nm"
        cflags = "-fPIC -O2" if self.settings.build_type != "Debug" else "-fPIC -g"
        # R33: 编译器/标志取自 Conan conf，不裸用 ${CC}/${CFLAGS}
        self.run(f"make -C {self.source_folder} CC={cc} AR={ar} NM={nm} "
                 f"CFLAGS='{cflags}' OUT_DIR={self.build_folder} -j1")

    def package(self):
        # 头文件保持 include/fixed_point/ 结构（复制 include 下全部 .h，保留相对路径）
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "fixed_point.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # 静态库统一命名为 libfixed_point.a
        os.rename(os.path.join(self.package_folder, "lib", "fixed_point.a"),
                  os.path.join(self.package_folder, "lib", "libfixed_point.a"))

    def package_info(self):
        # 公开 API 仅在定义 FXP_C99_INLINE 时声明（与上游默认用法一致）
        self.cpp_info.defines = ["FXP_C99_INLINE"]
        self.cpp_info.libs = ["fixed_point"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
