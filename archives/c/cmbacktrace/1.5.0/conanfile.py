#!/usr/bin/env python3
"""Conan recipe for cmbacktrace 1.5.0 — ARM Cortex-M fault backtrace library.

Source-drop C library: no configure/make/CMake in upstream. The library is a
single translation unit (cm_backtrace/cm_backtrace.c) plus headers, designed to
be dropped into an embedded project. We compile the TU into a static library
and package headers + lib.

Adaptation notes (OHOS aarch64):
  - cmb_cfg.h is patched (0001) to provide usable defaults: printf-based
    cmb_println, bare-metal platform, Cortex-M4 CPU type, English output.
  - cm_backtrace.c is patched (0002) to make the four linker-script symbols
    (CMB_CSTACK_BLOCK_START/END, CMB_CODE_SECTION_START/END) weak, so the
    library links without a Cortex-M linker script; a consumer that defines
    real stack/code bounds overrides them.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CmbacktraceConan(ConanFile):
    name = "cmbacktrace"
    version = "1.5.0"
    description = "CmBackTrace: C library for ARM Cortex-M fault backtrace (adapted for OHOS)"
    license = "MIT"
    homepage = "https://github.com/armink/CmBackTrace"
    url = "https://github.com/armink/CmBackTrace"

    package_type = "library"

    # Conan 2 强制 library 类型声明 shared 选项（G1 硬性校验）。
    # 本库为 source-drop 静态交付，默认/唯一形态为静态；保留选项以满足
    # 框架约束，build() 恒编译 .a（shared 不启用，见 build() 注释）。
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf (dict form), never bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        src_dir = os.path.join(self.source_folder, "cm_backtrace")
        obj = os.path.join(self.build_folder, "cm_backtrace.o")
        lib = os.path.join(self.build_folder, "libcmbacktrace.a")
        # Single TU: cm_backtrace.c includes headers + Languages/ via its own dir.
        self.run(f"{cc} -std=c99 -O2 -fPIC -I{src_dir} -c {os.path.join(src_dir, 'cm_backtrace.c')} -o {obj}")
        self.run(f"{ar} rcs {lib} {obj}")

    def package(self):
        src_dir = os.path.join(self.source_folder, "cm_backtrace")
        inc = os.path.join(self.package_folder, "include")
        copy(self, "cm_backtrace.h", src=src_dir, dst=inc)
        copy(self, "cmb_def.h", src=src_dir, dst=inc)
        copy(self, "cmb_cfg.h", src=src_dir, dst=inc)
        copy(self, "libcmbacktrace.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["cmbacktrace"]
