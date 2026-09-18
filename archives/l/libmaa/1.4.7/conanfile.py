#!/usr/bin/env python3
"""Conan recipe — libmaa 1.4.7

Memory Allocator Abstraction / low-level data structures library (dict.org / DICT project).
Provides hash tables, sets, lists, stacks, strings, argument parsing, base26/base64, etc.

Build system: BSD make (mk-configure / mkc), which is NOT compatible with GNU make.
This recipe performs the equivalent build steps directly with the toolchain compiler
(validated on HarmonyOS PC aarch64):

  1. generate arggram.c from arggram.txt via awk (required by arg.c)
  2. compile all sources to position-independent objects
     - SIZEOF_LONG=8: mkc would detect sizeof(long) at configure time; aarch64 long=8
     - HAVE_HEADER_SYS_RESOURCE_H=1: mkc header detection; sys/resource.h exists on OHOS
  3. archive static libmaa.a + link shared libmaa.so.4.0
  4. install headers (maa.h) and libraries

License: MIT
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, mkdir, rmdir, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibmaaConan(ConanFile):
    name = "libmaa"
    version = "1.4.7"
    description = "Library with low-level data structures (hash, set, list, string, arg parsing) helpful for writing compilers"
    license = "MIT"
    homepage = "https://github.com/cheusov/libmaa"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility (os may be "OHOS" or "Linux")
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("c") or "clang"

    def build(self):
        apply_conandata_patches(self)
        cc = self._get_cc()
        src = self.source_folder
        objdir = os.path.join(self.build_folder, "obj")
        mkdir(self, objdir)

        # 1) generate arggram.c (arg.c dependency)
        self.run('awk -f arggram2c arggram.txt > arggram.c', cwd=os.path.join(src, "maa"))

        # 2) compile all sources (full upstream list, incl. bit.c/timer.c)
        srcdir = os.path.join(src, "maa")
        sources = [
            "xmalloc.c", "hash.c", "set.c", "stack.c", "list.c", "error.c",
            "memory.c", "string.c", "debug.c", "flags.c", "maa.c", "prime.c",
            "bit.c", "timer.c", "arg.c", "pr.c", "sl.c", "base64.c", "base26.c",
            "source.c", "parse-concrete.c", "text.c", "log.c", "arggram.c",
        ]
        cflags = "-O2 -fPIC -I. -DMAA_MAJOR=4 -DMAA_MINOR=0 -DMAA_TEENY=0 " \
                 "-DSIZEOF_LONG=8 -DHAVE_HEADER_SYS_RESOURCE_H=1"
        for src_name in sources:
            obj = os.path.join(objdir, src_name.replace(".c", ".o"))
            self.run(f'{cc} -c {cflags} {src_name} -o {obj}', cwd=srcdir)

        # 3) static + shared libraries
        objs = " ".join(os.path.join(objdir, s.replace(".c", ".o")) for s in sources)
        build_dir = self.build_folder
        self.run(f'llvm-ar rc {build_dir}/libmaa.a {objs}', cwd=srcdir)
        self.run(f'llvm-ranlib {build_dir}/libmaa.a', cwd=srcdir)
        if self.options.shared:
            # soname 软链: libmaa.so.4.0 <- libmaa.so.4 <- libmaa.so（W4 审计 P2 修复）
            self.run(f'{cc} -shared -fPIC -Wl,-soname,libmaa.so.4 '
                     f'-o {build_dir}/libmaa.so.4.0 {objs} -lm', cwd=srcdir)
            self.run(f'rm -f {build_dir}/libmaa.so.4 {build_dir}/libmaa.so '
                     f'&& ln -s libmaa.so.4.0 {build_dir}/libmaa.so.4 '
                     f'&& ln -s libmaa.so.4 {build_dir}/libmaa.so', cwd=srcdir)

    def package(self):
        build_dir = self.build_folder
        copy(self, "libmaa.a", src=build_dir, dst=os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            copy(self, "libmaa.so.4.0", src=build_dir, dst=os.path.join(self.package_folder, "lib"))
            copy(self, "libmaa.so.4", src=build_dir, dst=os.path.join(self.package_folder, "lib"))
            copy(self, "libmaa.so", src=build_dir, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "maa.h", src=os.path.join(self.source_folder, "maa"),
             dst=os.path.join(self.package_folder, "include"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = ["maa"]
