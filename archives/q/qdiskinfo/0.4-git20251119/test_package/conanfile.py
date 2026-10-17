#!/usr/bin/env python3
"""Conan test_package — qdiskinfo 0.4-git20251119 (消费者侧验证).

上游 QDiskInfo 没有自动化测试套件（无 tests/、无 CTest；.github/workflows/
build.yaml 只做 cmake --build，无 test 步骤），因此本 test_package 承担
R51 的"补齐测试用例"职责，分两层：

  第 1 层（test_qdiskinfo，C++，链接 Qt6::Core）
    消费者视角冒烟：二进制存在/可执行、`--version`/`--help` 无 GUI 早期
    退出、`--ascii-view` 在无 root 时的明确报错、GUI 在 offscreen QPA 下
    能完成 Qt 平台插件加载与主窗口构造（不崩溃）。

  第 2 层（本文件的 test()，集成场景）
    验证 OHOS 适配补丁 0004 的实质行为：用日志桩 smartctl 顶替真实
    smartctl 并置于 PATH 首位，启动 GUI，断言
      a) 非特权路径执行了 `smartctl --scan --json`；
      b) 特权路径最终执行了 `smartctl -x --json=o /dev/qdiskinfo-test`。
    (b) 是提权回退生效的直接证据：HarmonyOS PC 没有 polkit/pkexec，
    上游写法 `QProcess::start("pkexec", ...)` 会启动失败且不产生任何调用，
    桩日志里不会出现 -x 调用。反之若桩日志出现 -x 调用，说明
    `Utils.startProcess()` 已正确降级为直接执行。
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import chmod, save

_GUI_SECONDS = 8


class QdiskinfoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # qtbase 以 cmake_find_mode=none 导出自身的 Qt6Config.cmake，
        # 必须把它的 cmake 目录放进 CMAKE_PREFIX_PATH 才能 find_package(Qt6)。
        qt_prefix = self.dependencies["qtbase"].package_folder
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_PREFIX_PATH"] = f"{qt_prefix}/lib/cmake"
        tc.generate()
        # conanrun：Qt 共享库 LD_LIBRARY_PATH、QT_PLUGIN_PATH、
        # 以及 smartmontools 贡献的 smartctl PATH。
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ── 第 2 层：提权回退集成场景 ────────────────────────────────
    def _privilege_fallback_scenario(self, app_bin):
        if shutil.which("pkexec"):
            # 非 OHOS 主机（有 polkit）不适用本断言：真实 pkexec 需要
            # polkit agent，无法在无人值守测试里完成授权。
            self.output.warning("检测到 pkexec（非 OHOS 主机），跳过提权回退场景")
            return

        scratch = os.path.join(self.build_folder, "privilege-fallback")
        bindir = os.path.join(scratch, "bin")
        home = os.path.join(scratch, "home")
        tmp = os.path.join(scratch, "tmp")
        for d in (bindir, home, tmp):
            os.makedirs(d, exist_ok=True)
        log = os.path.join(scratch, "smartctl-calls.log")
        stub = os.path.join(bindir, "smartctl")

        save(self, stub, f"""#!/bin/sh
# 桩 smartctl（仅测试用）：记录每次调用的参数；对 --scan 返回一个假设备，
# 其余调用（特权路径的 -x）静默退出，避免让 GUI 解析不完整 JSON。
echo "$@" >> "{log}"
for arg in "$@"; do
    if [ "$arg" = "--scan" ]; then
        printf '{{"devices":[{{"name":"/dev/qdiskinfo-test","type":"scsi"}}]}}'
        exit 0
    fi
done
exit 0
""")
        chmod(self, stub, execute=True)  # Conan>=2.15: chmod(self, path, read/write/execute)

        # PATH 首位注入桩目录；GUI 用 offscreen QPA，$GUI_SECONDS 后强杀。
        script = (
            f'PATH="{bindir}:$PATH"\n'
            "export PATH\n"
            "QT_QPA_PLATFORM=offscreen\n"
            "export QT_QPA_PLATFORM\n"
            f'HOME="{home}"\n'
            "export HOME\n"
            f'TMPDIR="{tmp}"\n'
            "export TMPDIR\n"
            f'"{app_bin}" &\n'
            "app_pid=$!\n"
            f"sleep {_GUI_SECONDS}\n"
            "kill -9 $app_pid 2>/dev/null || true\n"
            "wait $app_pid 2>/dev/null || true\n"
            "exit 0\n"
        )
        self.run(script, env="conanrun")

        calls = Path(log).read_text(encoding="utf-8") if os.path.exists(log) else ""
        self.output.info(f"桩 smartctl 调用记录:\n{calls.strip() or '(无)'}")

        scan_ok = "--scan" in calls
        fallback_ok = ("-x" in calls and "--json=o" in calls
                       and "/dev/qdiskinfo-test" in calls)
        if not scan_ok:
            raise ConanException(
                "非特权路径未调用 `smartctl --scan`：桩日志为空 → "
                "getSmartctlPath() 未解析到打包环境中的 smartctl")
        if not fallback_ok:
            raise ConanException(
                "特权路径未执行 `smartctl -x --json=o <device>`："
                "提权回退（补丁 0004）未生效，QProcess 可能仍在使用 pkexec")
        self.output.info("提权回退场景通过：--scan 与 -x 调用均被直接执行")

    def test(self):
        app_bin = os.path.join(
            self.dependencies["qdiskinfo"].package_folder, "bin", "QDiskInfo")
        if not os.path.isfile(app_bin):
            raise ConanException(f"打包产物缺少可执行文件: {app_bin}")

        if not can_run(self):
            return

        scratch = os.path.join(self.build_folder, "run-env")
        home = os.path.join(scratch, "home")
        tmp = os.path.join(scratch, "tmp")
        for d in (home, tmp):
            os.makedirs(d, exist_ok=True)

        # 第 1 层：消费者冒烟程序（链接 Qt6::Core，内部逐项断言并打印
        # "RESULT: N/N checks passed"，失败时返回非 0 → conan 测试失败）
        smoke = os.path.join(self.cpp.build.bindir, "test_qdiskinfo")
        self.run(f'HOME="{home}" TMPDIR="{tmp}" "{smoke}" "{app_bin}"',
                 env="conanrun")

        # 第 2 层：OHOS 提权回退集成场景
        self._privilege_fallback_scenario(app_bin)
