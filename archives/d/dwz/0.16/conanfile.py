#!/usr/bin/env python3
"""Conan recipe — dwz 0.16 (custom sh configure + Makefile).

DWARF compression tool (sourceware.org). Compresses .debug_* sections in
ELF binaries; used by debugedit's find-debuginfo for -g (gdb-index) tests.

OHOS adaptation notes:
- Build: custom sh `configure` + Makefile (uses CC/CPPFLAGS/CFLAGS/LDFLAGS/
  LIBS; LIBS=-lelf -lxxhash). No autotools — pass flags directly.
- Dep: elfutils (libelf, ohpcd) + libxxhash (ohpcd).
- Deps: libelf/libdw symbols resolved via -L/-Wl,-rpath to elfutils package.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class DwzConan(ConanFile):
    name = "dwz"
    version = "0.16"
    description = "DWARF compression tool"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceware.org/dwz/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def requirements(self):
        self.requires("elfutils/0.195", transitive_headers=True, transitive_libs=True)
        self.requires("libxxhash/0.8.3", transitive_headers=True, transitive_libs=True)
        # OHOS musl 无 glibc obstack.h（dwz 的 obstack-wrapper.h 需要）→
        # musl-obstack/1.2.3（ohpcd）提供
        self.requires("musl-obstack/1.2.3", transitive_headers=True, transitive_libs=True)

    def layout(self):
        # dwz 是 in-source 构建：源码自带 Makefile（自定义 sh configure），
        # make 需在源码树运行——source/build 同目录（dhcpcd 同款）
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        # tarball 解压为 dwz/ 单层目录 → strip_root=True 平铺到 source_folder
        # 根（Makefile 在源码根，in-source make 才能找到）
        get(self, **self.conan_data["sources"], strip_root=True)
        self._patch_compat_error_h()

    def _patch_compat_error_h(self):
        """OHOS musl 无 glibc 的 <error.h>（error()/error_at_line() 族）——
        写 compat error.h 到 include/，make 时 CPPFLAGS 注入 -Iinclude
        （debugedit 同款方案）。"""
        hdr_dir = os.path.join(self.source_folder, "include")
        os.makedirs(hdr_dir, exist_ok=True)
        compat = """/* OHOS musl compat: glibc <error.h> absent — minimal stand-in. */
#ifndef _OHOS_COMPAT_ERROR_H
#define _OHOS_COMPAT_ERROR_H
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
static inline void error(int status, int errnum, const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    fflush(stdout);
    fprintf(stderr, "dwz: ");
    vfprintf(stderr, fmt, ap);
    if (errnum != 0) fprintf(stderr, ": %s", strerror(errnum));
    fputc('\\n', stderr);
    va_end(ap);
    if (status != 0) exit(status);
}
static inline void error_at_line(int status, int errnum, const char *fname,
                                 unsigned int lineno, const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    fflush(stdout);
    fprintf(stderr, "dwz:%s:%u: ", fname, lineno);
    vfprintf(stderr, fmt, ap);
    if (errnum != 0) fprintf(stderr, ": %s", strerror(errnum));
    fputc('\\n', stderr);
    va_end(ap);
    if (status != 0) exit(status);
}
#endif
"""
        with open(os.path.join(hdr_dir, "error.h"), "w") as f:
            f.write(compat)
        self.output.info("wrote include/error.h (OHOS musl compat, debugedit same pattern)")

    def build(self):
        elf = self.dependencies["elfutils"]
        xxh = self.dependencies["libxxhash"]
        obst = self.dependencies["musl-obstack"]
        incs = " ".join("-I" + p for p in dict.fromkeys(
            [os.path.join(self.source_folder, "include")]  # compat error.h
            + list(elf.cpp_info.includedirs) + list(xxh.cpp_info.includedirs)
            + list(obst.cpp_info.includedirs)))
        libdirs = " ".join("-L" + p for p in dict.fromkeys(
            list(elf.cpp_info.libdirs) + list(xxh.cpp_info.libdirs)
            + list(obst.cpp_info.libdirs)))
        rpaths = " ".join("-Wl,-rpath," + p for p in dict.fromkeys(
            list(elf.cpp_info.libdirs) + list(xxh.cpp_info.libdirs)
            + list(obst.cpp_info.libdirs)))
        cc = "/data/service/hnp/bin/clang"
        env = {
            "CC": cc,
            "CPPFLAGS": incs,
            "LDFLAGS": f"{libdirs} {rpaths}",
        }
        for k, v in env.items():
            self.output.info(f"dwz build env {k}={v}")
        with open("Makefile.dwz.env", "w") as f:
            f.write("CC=%s\nCPPFLAGS=%s\nLDFLAGS=%s\n" % (cc, incs, f"{libdirs} {rpaths}"))
        # LIBS 覆盖：Makefile 只有 -lelf -lxxhash，缺 musl-obstack（dwz 的
        # obstack-wrapper.h 用 _obstack_begin/_obstack_free 等符号）
        self.run(f"make CC='{cc}' CPPFLAGS='{incs}' LDFLAGS='{libdirs} {rpaths}' LIBS='-lelf -lxxhash -lobstack' -j4")

    def package(self):
        copy(self, "dwz", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.RUNTIME", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
