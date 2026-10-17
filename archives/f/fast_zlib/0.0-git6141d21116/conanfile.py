#!/usr/bin/env python3
"""Conan recipe for fast_zlib 0.0-git6141d21116 — 自定义构建 (genmake 直接编译).

fast_zlib 是 zlib 的快速 longest_match 替换实现（C 版本，跨架构）。
构建方式（与上游 test.project 的 TYPE=C 目标等价）：
  1. 下载 fast_zlib 快照 + zlib 1.2.13 官方源码（zlib_sources → zlib/）
  2. 应用官方 Sources/zlib_1.2.13.patch（patches/zlib_1.2.13.patch，base_path=zlib）
  3. 编译 zlib 公共源码 + Test/deflate_stub.c（内含 deflate.c + match.h）→ libz.a

zlib 是系统同名库（R26），因此强制静态库（static-library, -fPIC）。
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# 上游 test.project COMMON_FILES（zlib 公共源码，不含 deflate.c —— deflate 由
# Test/deflate_stub.c 提供（ASMV + match.h 快速实现））
ZLIB_COMMON_SOURCES = [
    "adler32", "compress", "crc32", "gzclose", "gzlib", "gzread", "gzwrite",
    "infback", "inffast", "inflate", "inftrees", "trees", "uncompr", "zutil",
]


class FastZlibConan(ConanFile):
    name = "fast_zlib"
    version = "0.0-git6141d21116"
    description = "Heavily optimized zlib compression algorithm (fast longest_match for zlib)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/gildor2/fast_zlib"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"
    package_type = "static-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # zlib 1.2.13 源码需放在上游约定的 zlib/ 目录
        get(self, **self.conan_data["zlib_sources"], destination="zlib", strip_root=True)

    def _cc(self) -> str:
        """取 profile 注入的编译器（R33: 不依赖未定义的 shell 环境变量）。"""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return (compilers or {}).get("c", "clang")

    def _detect_sysroot(self) -> str:
        """从 conanbuild.sh 提取 --sysroot（若 profile 注入）。"""
        import re
        gen = self.generators_folder
        candidates = []
        main = os.path.join(gen, "conanbuild.sh")
        if os.path.isfile(main):
            candidates.append(main)
            try:
                with open(main) as fh:
                    for line in fh:
                        m = re.match(r'\.\s+"([^"]+)"', line.strip())
                        if m and os.path.isfile(m.group(1)):
                            candidates.append(m.group(1))
            except OSError:
                pass
        for path in candidates:
            try:
                with open(path) as fh:
                    content = fh.read()
                m = re.search(r"--sysroot=(\S+)", content)
                if m:
                    return m.group(1).rstrip('"').rstrip("'")
            except OSError:
                continue
        return ""

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        archiver = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        sysroot = self._detect_sysroot()

        src = self.source_folder
        zlib_dir = os.path.join(src, "zlib")
        build_dir = self.build_folder

        cflags = "-O2 -fPIC -DUNALIGNED_OK"
        if sysroot:
            cflags += f" --sysroot={sysroot}"

        objects = []
        for base in ZLIB_COMMON_SOURCES:
            obj = os.path.join(build_dir, base + ".o")
            c_src = os.path.join(zlib_dir, base + ".c")
            self.run(f'"{cc}" {cflags} -c -I "{zlib_dir}" -o "{obj}" "{c_src}"')
            objects.append(obj)
        # deflate 使用 stub：defines ASMV + include deflate.c + match.h
        stub_obj = os.path.join(build_dir, "deflate_stub.o")
        stub_src = os.path.join(src, "Test", "deflate_stub.c")
        self.run(f'"{cc}" {cflags} -c -I "{zlib_dir}" -o "{stub_obj}" "{stub_src}"')
        objects.append(stub_obj)

        libz = os.path.join(build_dir, "libz.a")
        objs_args = " ".join(f'"{o}"' for o in objects)
        self.run(f'"{archiver}" rcs "{libz}" {objs_args}')

    def package(self):
        pkg_lib = os.path.join(self.package_folder, "lib")
        pkg_inc = os.path.join(self.package_folder, "include")
        copy(self, "libz.a", dst=pkg_lib, src=self.build_folder)
        copy(self, "zlib.h", dst=pkg_inc, src=os.path.join(self.source_folder, "zlib"))
        copy(self, "zconf.h", dst=pkg_inc, src=os.path.join(self.source_folder, "zlib"))

    def package_info(self):
        self.cpp_info.libs = ["z"]
        self.cpp_info.set_property("cmake_file_name", "fast_zlib")
        self.cpp_info.set_property("cmake_target_name", "fast_zlib::fast_zlib")