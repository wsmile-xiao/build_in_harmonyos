#!/usr/bin/env python3
"""Conan test_package — libayatana-indicator 0.9.5 消费者测试.

走 PkgConfigDeps 链路消费 ayatana-indicator3-0.4.pc（pkg-config 完整传播
gtk→pango→harfbuzz 等传递依赖 include/lib，同 ayatana-ido 0.10.4 先例）。

上游 tests/ 依赖 dbus-test-runner / Xvfb / gtester 桌面环境（D-Bus session
bus、X11 display），CI 离线环境不可执行——不伪造。本测试覆盖：
  1. GObject 类型系统 + 核心对象生命周期（离线纯逻辑）
  2. IndicatorDesktopShortcuts 纯逻辑分支（无 X11/D-Bus 依赖）
  3. HarmonyOS 专项：ELF64 AArch64 架构 + NEEDED 段含
     libayatana-indicator3.so.7 + RPATH/RUNPATH 检查
"""
import os
import subprocess
import time

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class LibayatanaIndicatorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # glib 包发布的 glib-2.0.pc 缺 -lintl（同 gtk/3.24.43 与
        # ayatana-ido/0.10.4 先例）：test_package 链接期 undefined
        # reference g_libintl_ngettext，对 .pc 的 Libs 追加 -lintl。
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
        # 依赖图全部 libdir 注入 LD_LIBRARY_PATH（同 ayatana-ido 先例：
        # CI 干净环境 ctest 与直接运行均可达传递依赖共享库）。
        dep_libdirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir):
                    dep_libdirs.append(libdir)
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ":".join(dep_libdirs + ([existing] if existing else []))
        self.output.info("injected LD_LIBRARY_PATH: %d dep libdirs" % len(dep_libdirs))

        # 无窗口系统环境：启动 gtk 包自带 broadwayd 无头显示服务，
        # GDK_BACKEND=broadway（同 ayatana-ido 先例，gtk_init 需要 display）。
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
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libayatana-indicator")
            if os.path.isfile(bin_path):
                self.run(bin_path, env="conanrun")

            # ─── HarmonyOS 专项检查 ───────────────────────────────
            # ELF64 AArch64 + NEEDED 段 + RPATH/RUNPATH（W4/L5 同源要求）
            self._ohos_elf_check(bin_path)
        finally:
            if proc is not None:
                proc.terminate()

    def _ohos_elf_check(self, bin_path):
        llvm_readelf = self._find_llvm_readelf()
        if not llvm_readelf:
            self.output.warning("llvm-readelf not found; skip ELF check")
            return
        out = subprocess.run(
            [llvm_readelf, "-h", "-d", bin_path],
            capture_output=True, text=True, check=True,
        ).stdout

        # 1. ELF64 + AArch64
        is_elf64 = "Class:                             ELF64" in out
        is_aarch64 = "Machine:                           AArch64" in out
        if is_elf64 and is_aarch64:
            self.output.info("OHOS check: ELF64 AArch64 ✓")
        else:
            raise Exception("OHOS ELF check failed: not ELF64/AArch64 (64bit=%s, aarch64=%s)"
                            % (is_elf64, is_aarch64))

        # 2. NEEDED 段：共享形态必须含 libayatana-indicator3.so.7（SONAME）
        needed = [l.split("[")[1].rstrip("]") for l in out.splitlines()
                  if "NEEDED" in l and "[" in l]
        if self.dependencies["libayatana-indicator"].options.shared:
            if "libayatana-indicator3.so.7" not in needed:
                raise Exception("OHOS NEEDED check failed: libayatana-indicator3.so.7 "
                                "not in NEEDED: %s" % needed)
            self.output.info("OHOS check: NEEDED contains libayatana-indicator3.so.7 ✓")
        else:
            # static 形态：符号已并入消费者，NEEDED 不应出现本库
            if "libayatana-indicator3.so.7" in needed:
                raise Exception("OHOS NEEDED check failed (static): "
                                "libayatana-indicator3.so.7 should not be in NEEDED")
            self.output.info("OHOS check: static consumer, no lib NEEDED ✓")

        # 3. RPATH/RUNPATH：不得指向构建目录（绝对路径泄漏）
        for line in out.splitlines():
            if ("RPATH" in line or "RUNPATH" in line) and "/build/" in line:
                raise Exception("OHOS RPATH check failed: build dir leaked: %s" % line.strip())
        self.output.info("OHOS check: RPATH/RUNPATH clean ✓")

    def _find_llvm_readelf(self):
        # 优先 OHOS SDK llvm-readelf，其次 PATH 上的 llvm-readelf/readelf
        candidates = [
            "llvm-readelf",
            "readelf",
        ]
        # CC 的同目录 llvm-readelf 优先（OHOS SDK 工具链）
        clang = os.environ.get("CC") or ""
        if clang:
            candidates.insert(0, os.path.join(os.path.dirname(clang), "llvm-readelf"))
        for c in candidates:
            try:
                subprocess.run([c, "--version"], capture_output=True, timeout=10)
                return c
            except (OSError, subprocess.TimeoutExpired):
                continue
        return None
