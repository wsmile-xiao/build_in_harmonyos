import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["dietlibc"].cpp_info
        # R34/L1e：显式校验包内产物路径，避免 fallback 到系统 libc 头/库（OHOS 系统自带 musl libc）。
        for p in dep.includedirs:
            if not os.path.isdir(p):
                raise ConanException(f"dietlibc package include dir missing: {p}")
        libdir = dep.libdirs[0]
        if not os.path.isdir(libdir):
            raise ConanException(f"dietlibc package lib dir missing: {libdir}")
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        inc = " ".join("-isystem " + p for p in dep.includedirs)
        # dietlibc 是 libc 本体：必须用其头文件 + 启动对象 + 静态库，-nostdlib 静态链接。
        # 链接顺序对齐上游 Makefile t 目标：test.c start.o dyn_start.o dietlibc.a [builtins] dyn_stop.o
        # dietlibc 用 TLS（__thread），clang 用 emulated TLS，需显式链接 compiler-rt builtins
        # （提供 __emutls_get_address）；--rtlib=compiler-rt 在 -nostdlib 下不生效，故用完整路径。
        import subprocess
        try:
            builtins = subprocess.check_output(
                [cc, "-print-libgcc-file-name"], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            builtins = ""
        self.run(
            f'{cc} -nostdlib {inc} -static -no-pie -o test_probe '
            f'test.c {libdir}/start.o {libdir}/dyn_start.o '
            f'-Wl,--start-group {libdir}/dietlibc.a {builtins} {libdir}/libpthread.a -Wl,--end-group '
            f'{libdir}/dyn_stop.o'
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        self.run("./test_probe", env="conanrun")
