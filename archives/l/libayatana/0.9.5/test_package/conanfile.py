#!/usr/bin/env python3
"""Conan test_package — libayatana 0.9.5 消费者测试.

上游 ayatana-indicator3-0.4.pc 声明 Requires: gtk+-3.0 glib-2.0
libayatana-ido3-0.4，而 gtk+-3.0 传递依赖 pango→harfbuzz（hb.h）。
用 PkgConfigDeps 生成 .pc 并走 pkg_check_modules(IMPORTED_TARGET) 链接，
pkg-config 会完整传播 pango/harfbuzz/cairo 等传递 include/lib 路径
（同 ayatana-ido/gtk 先例），避免 CMakeDeps 组件图断裂导致 hb.h 找不到。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class LibayatanaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # PkgConfigDeps 生成的 glib-2.0.pc 缺少 -lintl（Libs 无 intl 符号），
        # 而 libayatana-indicator3.so → libayatana-ido3-0.4.so 引用
        # g_libintl_ngettext；同 gtk/3.24.43/ayatana-ido 先例：给生成的
        # glib-2.0.pc 的 Libs 追加 -lintl，否则 test_package 可执行链接报
        # undefined reference (--no-allow-shlib-undefined 强制)。
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.isfile(pc):
            content = open(pc, encoding="utf-8").read()
            lines = []
            for line in content.splitlines(keepends=True):
                if line.startswith("Libs:") and "-lintl" not in line.split():
                    line = line.rstrip("\r\n") + " -lintl\n"
                lines.append(line)
            new_content = "".join(lines)
            if new_content != content:
                open(pc, "w", encoding="utf-8", newline="\n").write(new_content)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 显式把依赖图全部 libdir 注入 LD_LIBRARY_PATH（同 ayatana-ido
        # 先例），保证 CI 干净环境 ctest 与直接运行均可达传递依赖共享库。
        dep_libdirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir):
                    dep_libdirs.append(libdir)
        # 系统 libc++_shared.so 位于 /system/lib64（harfbuzz 等动态库依赖），
        # conan 干净环境 LD_LIBRARY_PATH 为空，需显式追加系统目录。
        sys_dirs = ["/system/lib64", "/system/lib64/platformsdk",
                    "/system/lib64/chipset-pub-sdk", "/system/lib64/ndk"]
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ":".join(dep_libdirs + sys_dirs + ([existing] if existing else []))
        self.output.info("injected LD_LIBRARY_PATH: %d dep libdirs + system dirs" % len(dep_libdirs))

        cmake = CMake(self)
        cmake.test()
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libayatana")
        if os.path.isfile(bin_path):
            self.run(bin_path, env="conanrun")