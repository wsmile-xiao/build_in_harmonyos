#!/usr/bin/env python3
"""Conan recipe — libalgebra 1.1.0 (header-only C/C++ library).

libalgebra (https://github.com/mklarqvist/libalgebra) is a single-header
C/C++ library for fast SIMD-friendly bit/byte statistics (popcount,
intersect/union count, sum of bytes, etc.). The official tarball contains
only libalgebra.h plus an x86-specific benchmark sample; there is no
compiled library artifact, so this recipe packages the header only.

Adaptation note: upstream libalgebra.h unconditionally included
<x86intrin.h> (guarded only by !_MSC_VER), which breaks compilation on
aarch64 (OHOS). Patch 0001-libalgebra.h.patch adds the same x86/x64
guard family already used elsewhere in the header (X86_OR_X64), so the
header compiles on ARM64 OHOS with the portable / builtin code paths.
The upstream benchmark.cpp is x86-only inline asm (CPUID/rdtsc) and is
NOT buildable on aarch64; it is not packaged here (header-only library).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, copy, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class LibalgebraConan(ConanFile):
    name = "libalgebra"
    version = "1.1.0"
    description = "libalgebra - header-only C/C++ library for fast popcount and bit/byte statistics"
    license = "Apache-2.0"
    homepage = "https://github.com/mklarqvist/libalgebra"
    url = ""  # CI fills this

    package_type = "header-library"

    # 无编译产物 → settings 仅保留结构一致性；package_id 清空见下
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    # 无编译阶段：不伪造编译日志（R34）——header-only 库无构建产物

    def package(self):
        copy(self, "*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
