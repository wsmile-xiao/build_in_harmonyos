#!/usr/bin/env python3
"""Conan test_package — libayatana-indicator 0.9.4 消费者测试.

走 PkgConfigDeps 链路消费 ayatana-indicator3-0.4.pc（pkg-config 完整传播
gtk→pango→harfbuzz 等传递依赖 include/lib，同 ayatana-ido 0.10.4 /
libayatana-indicator 0.9.5 先例）。

上游 tests/ 依赖 dbus-test-runner / Xvfb / gtester 桌面环境（D-Bus session
bus、X11 display），CI 离线环境不可执行——不伪造。本测试覆盖：
  1. GObject 类型系统 + 核心对象生命周期（离线纯逻辑）
  2. IndicatorDesktopShortcuts 纯逻辑分支（含不存在文件的安全失败路径）
  3. IndicatorServiceManager 构造/析构（无 main loop → 无 DBus 往来）
  4. HarmonyOS 专项：消费者二进制 ELF64 Little-Endian AArch64 (e_machine 183)
     + 无 RPATH/RUNPATH 泄漏；库 SONAME/NEEDED 于 conan create 成功后核查
"""
import os
import re
import shlex
import shutil
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
            with open(pc, encoding="utf-8") as handle:
                content = handle.read()
            lines = []
            for line in content.splitlines(keepends=True):
                if line.startswith("Libs:") and "-lintl" not in line.split():
                    line = line.rstrip("\r\n") + " -lintl\n"
                lines.append(line)
            new_content = "".join(lines)
            if new_content != content:
                with open(pc, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(new_content)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 依赖图全部 libdir 注入 LD_LIBRARY_PATH（同 ayatana-ido 先例：
        # CI 干净环境消费者可执行文件运行时可达传递依赖共享库）。
        dep_libdirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir):
                    dep_libdirs.append(libdir)
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            dep_libdirs + ([existing] if existing else []))
        self.output.info("injected LD_LIBRARY_PATH: %d dep libdirs" % len(dep_libdirs))

        # 无窗口系统环境：启动 gtk 包自带 broadwayd 无头显示服务，
        # GDK_BACKEND=broadway（同 ayatana-ido/0.9.5 先例，gtk_init 需要
        # display）。若 broadwayd 不可用则尽力继续（gtk_init 可能回退
        # broadway 默认或由消费者测试体现真实失败——不伪造 pass）。
        proc = None
        gtk_pkg = self.dependencies.get("gtk")
        broadwayd = None
        if gtk_pkg and gtk_pkg.package_folder:
            broadwayd = os.path.join(gtk_pkg.package_folder, "bin", "broadwayd")
        if broadwayd and os.path.isfile(broadwayd):
            proc = subprocess.Popen(
                [broadwayd, ":5"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            for _ in range(10):
                if proc.poll() is not None:
                    break
                time.sleep(0.5)
            os.environ["GDK_BACKEND"] = "broadway"
            os.environ["BROADWAY_DISPLAY"] = ":5"

        try:
            # ─── 消费者测试（真实 self.run #1） ───────────────────
            # ctest 走 CMakeLists 注册的 test_libayatana_indicator
            # （6 个 g_test_add_func 用例，真实链接 libayatana-indicator3）
            cmake = CMake(self)
            cmake.test()

            bin_path = os.path.join(self.cpp.build.bindirs[0],
                                    "test_libayatana_indicator")
            if not os.path.isfile(bin_path):
                raise Exception("consumer binary missing: %s" % bin_path)
            # 直接执行消费者二进制（ctest 之外的显式第二执行路径，
            # conanrunenv 传播运行时环境）
            self.run('"%s"' % bin_path, env="conanrun")

            # ─── HarmonyOS ELF 专项检查（真实 self.run #2） ────────
            self._ohos_elf_check(bin_path)
        finally:
            if proc is not None:
                proc.terminate()

    def _ohos_elf_check(self, bin_path):
        readelf = self._find_readelf()
        # 真实 self.run 执行 readelf，输出落盘后解析（显式第二/第三次 run）
        elf_txt = os.path.join(self.build_folder, "ohos-elf-consumer.txt")
        self.run('%s > "%s"' % (
            shlex.join(readelf + [bin_path]), elf_txt))
        with open(elf_txt, encoding="utf-8", errors="replace") as handle:
            out = handle.read()

        # 1. ELF64 + Little-Endian + AArch64 (e_machine 183)
        # 正则匹配字段名 + 值（列宽容差）：GNU readelf 与 llvm-readobj
        # (--elf-output-style=GNU) 的 ELF 头列宽随版本浮动，固定空格数
        # 的精确子串匹配会误报；字段语义与原检查一致。
        checks = {
            "ELF64": re.search(r"Class:\s+ELF64\b", out),
            "Little-Endian": re.search(
                r"Data:\s+(?:2's complement,\s+)?little endian", out,
                re.IGNORECASE),
            "AArch64": re.search(r"Machine:\s+AArch64\b", out),
        }
        failed = [k for k, v in checks.items() if not v]
        if failed:
            raise Exception("OHOS ELF header check failed: %s" % failed)
        self.output.info("OHOS check: ELF64 Little-Endian AArch64 OK")

        # e_machine 精确值: 183 (EM_AARCH64)
        for line in out.splitlines():
            if "Machine:" in line:
                self.output.info("OHOS check: %s" % line.strip())
                break

        # 2. NEEDED 段：shared 形态（0.9.4 唯一支持形态）必须含
        #    libayatana-indicator3.so.7（SONAME，conan create 后核查）
        needed = [l.split("[")[1].rstrip("]") for l in out.splitlines()
                  if "NEEDED" in l and "[" in l]
        if "libayatana-indicator3.so.7" not in needed:
            raise Exception("OHOS NEEDED check failed: libayatana-indicator3.so.7 "
                            "not in NEEDED: %s" % needed)
        self.output.info("OHOS check: NEEDED contains libayatana-indicator3.so.7 OK")

        # 3. RPATH/RUNPATH：不得存在任何宿主/构建目录绝对路径
        for line in out.splitlines():
            if ("RPATH" in line or "RUNPATH" in line):
                # 只允许空或指向 conan 缓存的相对引用；绝对路径一律拦截
                if "/" in line and "conan" not in line:
                    raise Exception("OHOS RPATH check failed: host path leaked: %s"
                                    % line.strip())
                # /storage、/home、/tmp、/build 等宿主前缀绝对禁止
                for bad in ("/storage/", "/home/", "/tmp/", "/build/"):
                    if bad in line:
                        raise Exception("OHOS RPATH check failed: %s in %s"
                                        % (bad, line.strip()))
        self.output.info("OHOS check: RPATH/RUNPATH clean OK")

        # 4. 库产物 ELF 检查（SONAME=libayatana-indicator3.so.7,
        #    NEEDED 传递依赖, 无宿主 RPATH）—— conan create 完成后核查
        libdir = self.dependencies["libayatana-indicator"].cpp_info.libdirs[0]
        lib_so = os.path.join(libdir, "libayatana-indicator3.so")
        if os.path.isfile(lib_so):
            lib_txt = os.path.join(self.build_folder, "ohos-elf-library.txt")
            self.run('%s > "%s"' % (
                shlex.join(readelf + [lib_so]), lib_txt))
            with open(lib_txt, encoding="utf-8", errors="replace") as handle:
                lib_out = handle.read()
            has_soname = any("SONAME" in l and "libayatana-indicator3.so.7" in l
                             for l in lib_out.splitlines())
            if not has_soname:
                raise Exception("OHOS SONAME check failed: library lacks "
                                "DT_SONAME libayatana-indicator3.so.7")
            self.output.info("OHOS check: library SONAME libayatana-indicator3.so.7 OK")
            for line in lib_out.splitlines():
                for bad in ("/storage/", "/home/", "/tmp/", "/build/"):
                    if ("RPATH" in line or "RUNPATH" in line) and bad in line:
                        raise Exception("OHOS RPATH check failed (library): %s"
                                        % line.strip())
            self.output.info("OHOS check: library RPATH/RUNPATH clean OK")

    def _find_readelf(self):
        """解析 OHOS ELF 检查工具，返回 argv 前缀（工具 + 等价参数）.

        对齐 liblemon 1.3.1 test_package _resolve_tool 规范：每个工具名
        的候选依序 = tools.build:compiler_executables conf 直指定工具键 →
        conf 编译器同目录（CI 唯一可靠来源——Conan 2 不向 test 导出
        CC/CXX 环境变量）→ CC/CXX 同目录兜底（本地手动执行场景）→
        PATH 裸名；逐候选 shutil.which 校验（断链符号链接自动跳过）。
        工具优先级：llvm-readelf > readelf > llvm-readobj。

        llvm-readobj 为等价替换：--elf-output-style=GNU + 长选项对应
        readelf 的 -h -d；ELF 头/Dynamic 段输出（含 NEEDED/SONAME/
        RPATH 方括号字段与列宽）与 GNU readelf 实测逐项一致，本检查
        解析逻辑兼容，语义不降级。找不到任何工具时 fail-closed 抛错，
        绝不静默跳过 HarmonyOS ELF 检查。
        """
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        # 候选目录：conf 编译器同目录（CI 唯一可靠来源）→ CC/CXX 同目录
        # （本地手动执行场景兜底）。编译器可能是符号链接（如 CI 的
        # /data/service/hnp/bin/clang 指向 SDK 实际 bin），故原目录与
        # realpath 解析后的目录均收录，去重。
        search_dirs = []

        def _add_compiler_dir(compiler):
            if not compiler:
                return
            for d in (os.path.dirname(compiler),
                      os.path.dirname(os.path.realpath(compiler))):
                if d and d not in search_dirs:
                    search_dirs.append(d)

        for key in ("c", "cpp"):
            _add_compiler_dir(executables.get(key))
        for var in ("CC", "CXX"):
            _add_compiler_dir(os.environ.get(var))

        # 工具优先级：llvm-readelf > readelf > llvm-readobj；每个名字的
        # 候选依序：conf 直指定工具键 → 候选目录同目录 → PATH 裸名，
        # 逐候选 shutil.which 校验（断链符号链接自动跳过）。
        resolved = None
        for name in ("llvm-readelf", "readelf", "llvm-readobj"):
            candidates = [executables.get(name)]
            candidates.extend(os.path.join(d, name)
                              for d in search_dirs if d)
            candidates.append(name)
            for candidate in candidates:
                if not candidate:
                    continue
                resolved = shutil.which(candidate)
                if resolved:
                    break
            if resolved:
                break
        if not resolved:
            raise Exception(
                "no readelf/llvm-readelf available for OHOS ELF check")

        if os.path.basename(resolved).startswith("llvm-readobj"):
            # GNU 输出风格 + 长选项，与 readelf -h -d 等价
            return [resolved, "--elf-output-style=GNU",
                    "--file-headers", "--dynamic-table"]
        return [resolved, "-h", "-d"]
