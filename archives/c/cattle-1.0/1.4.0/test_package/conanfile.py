#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class CattleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "PkgConfigDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        env = Environment()
        # cattle-1.0.pc 由 PkgConfigDeps 生成在 generators 目录，追加到
        # PKG_CONFIG_PATH（否则 pkg-config 找不到 cattle-1.0，编译失败）
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # glib 依赖链（glib/libffi/pcre2）的 lib/pkgconfig 全部追加到
        # PKG_CONFIG_PATH（glib-2.0.pc 的 Requires: libpcre2-8 需 libpcre2-8.pc
        # 在搜索路径，否则 pkg-config 解析失败导致 cattle/cattle.h 找不到）
        for dep_name in ("glib", "libffi", "pcre2"):
            try:
                dep = self.dependencies[dep_name]
            except (KeyError, AttributeError):
                continue
            pkgconfig_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pkgconfig_dir):
                env.prepend_path("PKG_CONFIG_PATH", pkgconfig_dir)
        env.vars(self).save_script("conanbuild_pkgconfig")

    def test(self):
        # 编译并运行 test_cattle.c：调用 cattle 公开 API（cattle_interpreter_new），
        # 验证库可实际编译链接运行（非空壳测试，R34）。$CC/$CFLAGS 来自
        # VirtualBuildEnv（env="conanbuild" 激活），pkg-config 提供 cattle/glib flags
        src = os.path.join(self.source_folder, "src", "test_cattle.c")
        test_bin = os.path.join(self.build_folder, "test_cattle")
        # 显式带出 glib include 路径（glib.h 在 include/glib-2.0，glibconfig.h
        # 在 lib/glib-2.0/include）：ohpcd glib 二进制包的 .pc Cflags 可能未
        # 带出，否则 cattle-version.h 的 #include <glib.h> 找不到
        glib = self.dependencies["glib"]
        glib_inc = (
            f"-I{os.path.join(glib.package_folder, 'include', 'glib-2.0')} "
            f"-I{os.path.join(glib.package_folder, 'lib', 'glib-2.0', 'include')}"
        )
        # 显式追加 glib 依赖链（glib/libffi/pcre2）的 -L lib 路径：pkg-config
        # --libs 只输出 -l 无有效 -L，否则链接时找不到 libglib-2.0/libpcre2-8
        lib_paths = " ".join(
            f"-L{os.path.join(self.dependencies[n].package_folder, 'lib')}"
            for n in ("glib", "libffi", "pcre2")
            if n in self.dependencies
        )
        # pkg-config --libs 输出缺 glib 库名（ohpcd glib 包 .pc Libs 无效，
        # 与 cflags 同类问题），显式追加 glib 依赖链 -l 库名
        # （-lffi：libgobject-2.0 的 gclosure.c 依赖 libffi，ffi_* 符号）
        libs = "-lglib-2.0 -lgobject-2.0 -lgio-2.0 -lffi"
        ret = self.run(
            f'${{CC:-clang}} ${{CFLAGS}} -o "{test_bin}" "{src}" '
            f"$(pkg-config --cflags --libs cattle-1.0 glib-2.0) {glib_inc} {lib_paths} {libs}",
            env="conanbuild",
        )
        if ret != 0:
            raise ConanException(f"test_cattle.c compilation failed with exit code {ret}")
        ret = self.run(f'"{test_bin}"', env="conanrun")
        if ret != 0:
            raise ConanException(f"test_cattle run failed with exit code {ret}")
        self.output.info("cattle-1.0 API verified successfully")