#!/usr/bin/env python3
"""Conan recipe — asprintf.c 0.0.3 (Makefile, static library).

asprintf.c 提供 POSIX asprintf()/vasprintf() 的独立实现。
构建系统：纯 Makefile（无 configure 脚本）。

关键适配点：
1. 上游 Makefile 只编译并运行 `test` 目标（test.c + asprintf.c），
   不产出任何库文件，也没有可用的 install 目标（`install: $(BIN)`
   中 $(BIN) 从未定义）。因此本配方用 R33 合规方式（从 Conan conf
   取编译器，不用裸 shell 变量）显式编译 asprintf.c 为静态库
   libasprintf.a，并安装公开头文件。
2. 上游官方测试入口为 `make test`（Makefile test 目标，编译 test.c
   并执行，3 组断言）。build() 内实际运行该入口以满足 L1 与
   双口径测试台账要求。
3. 包内无 bin/ 产物、无 CLI，按 R38 不需要 commands.json。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AsprintfCConan(ConanFile):
    name = "asprintf.c"
    version = "0.0.3"
    description = "asprintf() implementation (POSIX asprintf/vasprintf)"
    license = "MIT"
    homepage = "https://github.com/jwerle/asprintf.c"
    url = "https://github.com/jwerle/asprintf.c"
    topics = ("asprintf", "vasprintf", "printf", "string", "libc-extension")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 无第三方 Conan 依赖（仅依赖工具链与 OHOS musl sysroot）
        pass

    def layout(self):
        basic_layout(self)
        # 上游 Makefile 为 in-source 构建，构建目录即源码目录
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"

        cflags = "-std=c99 -Wall -Wextra -fPIC"

        # 1) 上游官方测试入口：make test（编译 test.c + asprintf.c 并执行，
        #    内含 3 组 asprintf 断言）。这是 L1 验证的上游测试。
        self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} CFLAGS=\"{cflags}\" test", cwd=self.source_folder)

        # 2) 显式编译静态库 libasprintf.a（上游 Makefile 无库目标）
        self.run(
            f"{cc} {cflags} -c asprintf.c -o libasprintf.a.tmp.o && "
            f"{ar} rcs libasprintf.a libasprintf.a.tmp.o && {ranlib} libasprintf.a",
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "asprintf.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "libasprintf.a", self.source_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["asprintf"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        # OHOS 设备无 pkg-config 消费场景，不生成 cmake 文件（静态库仅头文件+lib）
