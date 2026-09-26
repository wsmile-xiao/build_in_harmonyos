#!/usr/bin/env python3
"""test_package for xcfa 5.0.2 — 消费者测试（R34：真实执行被测包产物）。

test() 依次运行两个脚本，两者都真实调用包内安装的二进制：
1. test.sh      — 功能测试（上游行为视角）：GUI 二进制的 --version/--help、
                  xcfa_cli 的帮助横幅，以及 xcfa_cli 对一个真实 WAV 的
                  音频分析（frequency / quantification / 时长）
2. test_ohos.sh — 鸿蒙特有测试：ELF64/AArch64/PIE、musl 解释器
                  (/lib/ld-musl-aarch64.so.1)、OHOS ELF 标记
                  (.codesign/.note.ohos.ident)、无 RPATH/RUNPATH、无 glibc
                  专有动态依赖、可加载段内无构建机路径、bash 包裹可执行、
                  运行期上报 HarmonyOS/aarch64、GTK/GLib 运行期版本可用、
                  无显示服务时 --help 优雅退出、包内产物完备、全程无崩溃
"""
import os
import shutil

from conan import ConanFile


class XcfaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["xcfa"].package_folder
        gui = os.path.join(pkg, "bin", "xcfa")
        cli = os.path.join(pkg, "bin", "xcfa_cli")
        for binary in (gui, cli):
            if not os.path.isfile(binary):
                raise FileNotFoundError(f"packaged binary not found: {binary}")

        # OHOS: /system/bin/sh 不能直接 exec ELF；脚本一律由 bash 包裹执行。
        # 解析顺序：CONFIG_SHELL（profile buildenv）→ PATH 查找 →
        # /data/service/hnp/bin/bash（OHOS 固定路径）；都拿不到则 fail closed。
        # 用 os.path.isfile 而非 os.access(X_OK)：HMDFS 上 chmod 被忽略，
        # X_OK 恒 False（R49/E046），会把可用 bash 误判为不可用。
        bash = os.environ.get("CONFIG_SHELL", "")
        if not (bash and os.path.isfile(bash)):
            bash = shutil.which("bash") or ""
        if not (bash and os.path.isfile(bash)):
            fallback = "/data/service/hnp/bin/bash"
            bash = fallback if os.path.isfile(fallback) else ""
        if not bash:
            raise FileNotFoundError(
                "bash not found for test scripts "
                "(set CONFIG_SHELL or put bash on PATH)"
            )

        # 1) 功能测试（上游行为视角）
        self.run(
            f'"{bash}" test.sh "{gui}" "{cli}"',
            env="conanrun",
            cwd=self.source_folder,
        )
        # 2) 鸿蒙特有测试（平台特性 + 平台能力约束）
        self.run(
            f'"{bash}" test_ohos.sh "{gui}" "{cli}" "{pkg}"',
            env="conanrun",
            cwd=self.source_folder,
        )
        self.output.info("xcfa: functional + OHOS tests OK (5 + 14 assertions)")
