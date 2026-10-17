import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["picolibc"].cpp_info
        # R34/L1e：显式校验包内产物路径，避免 fallback 到系统 musl libc 头/库。
        for p in dep.includedirs:
            if not os.path.isdir(p):
                raise ConanException("picolibc include dir missing: %s" % p)
        libdir = dep.libdirs[0]
        if not os.path.isdir(libdir):
            raise ConanException("picolibc lib dir missing: %s" % libdir)
        for f in ("crt0.o", "libpicolibc.a", "libsemihost.a", "picolibc.ld"):
            if not os.path.isfile(os.path.join(libdir, f)):
                raise ConanException("picolibc package %s missing" % f)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        inc = " ".join("-isystem " + p for p in dep.includedirs)

        # compiler-rt builtins（picolibc 无 libgcc，-nostdlib 链接需运行时库）。
        try:
            builtins = subprocess.check_output(
                [cc, "-print-libgcc-file-name"], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            builtins = ""

        # clang 内置 include 目录：picolibc 的 string.h 等头通过 #include <stddef.h> 依赖
        # clang 内置头（freestanding 头），-nostdinc 下需显式 -isystem 提供（同 klibc）。
        try:
            clang_inc = subprocess.check_output(
                [cc, "--print-file-name=include"], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            clang_inc = ""
        if clang_inc:
            inc += " -isystem " + clang_inc

        # picolibc 是 bare-metal libc：-nostdlib -nostdinc + crt0.o + libpicolibc.a +
        # libsemihost.a（提供 _exit 等）+ compiler-rt builtins + -T picolibc.ld。
        # -static -no-pie：clang aarch64-linux-ohos 默认链动态 PIE，产生 .hash/.dynstr 等
        #   动态段与裸机 picolibc.ld 冲突，必须静态链接。
        # -Wl,--gc-sections + 扩大 __flash_size/__ram_size：picolibc.ld 默认 flash 仅
        #   0x10000，release 编译 + 完整 libc 会溢出，裁剪未用代码并扩大内存布局。
        # 只验证「编译 + 链接」，裸机 ELF 不运行。
        self.run(
            '%s -nostdlib -nostdinc %s '
            '-o test_probe test_picolibc.c %s/crt0.o '
            '-Wl,--start-group %s/libpicolibc.a %s/libsemihost.a %s -Wl,--end-group '
            '-static -no-pie -Wl,--gc-sections '
            '-Wl,--defsym=__flash_size=0x100000 -Wl,--defsym=__ram_size=0x100000 '
            '-Wl,-T %s/picolibc.ld'
            % (cc, inc, libdir, libdir, libdir, builtins, libdir)
        )

    def test(self):
        # picolibc 是 bare-metal libc，产物是裸机 ELF（加载到 0x10000000 flash、无 OS ABI），
        # 无法在 OHOS 用户态直接运行（无 .codesign、裸机内存布局、无 semihost 宿主）。
        # 编译+链接成功即证明消费者可用；如实说明不运行，不伪造通过。
        if os.path.isfile("test_probe"):
            self.output.info(
                "picolibc 消费者程序编译+链接成功（bare-metal libc，不运行裸机 ELF）"
            )
        else:
            raise ConanException("test_probe was not produced by link step")
