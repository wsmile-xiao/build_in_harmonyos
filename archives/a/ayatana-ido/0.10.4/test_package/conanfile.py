#!/usr/bin/env python3
"""Conan test_package — ayatana-ido 0.10.4 消费者测试.

上游 libayatana-ido3-0.4.pc 声明 Requires: gtk+-3.0 glib-2.0，而 gtk+-3.0
传递依赖 pango→harfbuzz（hb.h）。用 PkgConfigDeps 生成 .pc 并走
pkg_check_modules(IMPORTED_TARGET) 链接，pkg-config 会完整传播
pango/harfbuzz/cairo 等传递 include/lib 路径（同 gtk/3.24.43 先例），
避免 CMakeDeps 组件图断裂导致 hb.h 找不到。
"""
import os
import subprocess
import time

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class AyatanaidoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # glib 包发布的 glib-2.0.pc 缺少 -lintl（Libs 无 intl 符号），
        # 而 libayatana-ido3-0.4.so 引用 g_libintl_ngettext；同 gtk/3.24.43
        # 配方先例：给 PkgConfigDeps 生成的 glib-2.0.pc 的 Libs 追加 -lintl，
        # 否则 test_package 可执行链接报 undefined reference
        # (--no-allow-shlib-undefined 强制)。
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
        # 根因修复 (r02, PR #7826 test_package CI 失败):
        # 复现显示 ctest 直接加载 test_ayatana-ido 时, 传递依赖共享库
        # (libsharpyuv/libatk/libglib/libintl/libfribidi 等, 由 gtk/pango/cairo
        # 依赖图拉入) 在运行时不可达 -> "Error loading shared library
        # libsharpyuv.so.0" -> 符号 relocating 失败 -> Test Failed。
        # 显式把依赖图全部 libdir 注入 LD_LIBRARY_PATH (不依赖 conanrun 隐式
        # 注入), 保证 CI 干净环境 ctest 与直接运行均可达。
        dep_libdirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir):
                    dep_libdirs.append(libdir)
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ":".join(dep_libdirs + ([existing] if existing else []))
        self.output.info("injected LD_LIBRARY_PATH: %d dep libdirs" % len(dep_libdirs))

        # 无窗口系统环境（CI/HarmonyOS PC）：启动 gtk 包自带 broadwayd 无头
        # 显示服务，GDK_BACKEND=broadway 运行测试（同 xclip/Xvfb 先例；
        # 否则 gtk_init 报 cannot open display 测试失败）。
        broadwayd = None
        proc = None
        gtk_pkg = self.dependencies.get("gtk")
        if gtk_pkg and gtk_pkg.package_folder:
            broadwayd = os.path.join(gtk_pkg.package_folder, "bin", "broadwayd")
        if broadwayd and os.path.isfile(broadwayd):
            proc = subprocess.Popen(
                [broadwayd, ":5"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            # 就绪等待: 轮询进程存活, 最多 10×0.5s (slow-start CI 上固定
            # time.sleep(2) 可能未就绪; 进程早退则降级并保留诊断信息)。
            # 注意: 无 break——必须真正轮询满 range(10), 否则只 sleep 一次。
            ready = False
            for _ in range(10):
                if proc.poll() is not None:
                    break
                time.sleep(0.5)
            else:
                ready = True
            if not ready:
                self.output.warning("broadwayd not ready (rc=%s); display may be unavailable"
                                    % (proc.returncode if proc.poll() is not None else "still-alive"))
            os.environ["GDK_BACKEND"] = "broadway"
            os.environ["BROADWAY_DISPLAY"] = ":5"
        try:
            cmake = CMake(self)
            cmake.test()
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_ayatana-ido")
            if os.path.isfile(bin_path):
                self.run(bin_path, env="conanrun")
        finally:
            if proc is not None:
                proc.terminate()