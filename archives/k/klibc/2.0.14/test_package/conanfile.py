import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["klibc"].cpp_info
        # R34/L1e：显式校验包内产物路径，避免 fallback 到系统 musl libc 头/库。
        for p in dep.includedirs:
            if not os.path.isdir(p):
                raise ConanException(f"klibc package include dir missing: {p}")
        libdir = dep.libdirs[0]
        if not os.path.isdir(libdir):
            raise ConanException(f"klibc package lib dir missing: {libdir}")
        for f in ("crt0.o", "libklibc.a"):
            if not os.path.isfile(os.path.join(libdir, f)):
                raise ConanException(f"klibc package {f} missing")
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        inc = " ".join("-isystem " + p for p in dep.includedirs)
        # klibc 是 libc 本体：-nostdlib -nostdinc + crt0.o + libklibc.a + builtins 静态链接。
        # clang 用 emulated TLS/内置函数需 compiler-rt builtins（-print-libgcc-file-name）。
        try:
            builtins = subprocess.check_output(
                [cc, "-print-libgcc-file-name"], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            builtins = ""
        # clang 内置 include 目录：klibc 的 stdarg.h 用 #include_next <stdarg.h>，
        # 需在 -nostdinc 下显式提供 clang 内置头。
        try:
            clang_inc = subprocess.check_output(
                [cc, "--print-file-name=include"], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            clang_inc = ""
        self.run(
            f'{cc} -nostdlib -nostdinc {inc} -isystem {clang_inc} '
            f'-D__KLIBC__=2 -D__KLIBC_MINOR__=0 -D_BITSIZE=64 '
            f'-static -no-pie -o test_probe '
            f'test_klibc.c {libdir}/crt0.o '
            f'-Wl,--start-group {libdir}/libklibc.a {builtins} -Wl,--end-group'
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        self.run("./test_probe", env="conanrun")
