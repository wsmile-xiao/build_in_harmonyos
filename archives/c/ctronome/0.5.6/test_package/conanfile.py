#!/usr/bin/env python3
"""test_package for ctronome — 两个脚本都真实执行被测包产物（R34）。

test() 依次运行：
1. test.sh      — 功能测试（上游行为视角）：-h 用法 / -v 版本横幅 /
                  用包内 WAV 采样跑到音频输出阶段
2. test_ohos.sh — 鸿蒙特有测试（16 条）：ELF64/AArch64/PIE、musl 解释器
                  （/lib/ld-musl-aarch64.so.1）、无 RPATH/RUNPATH、仅 musl libc
                  动态依赖、OHOS ELF 标记（.codesign/.note.ohos.ident）、可加载
                  镜像与二进制内无构建机绝对路径、bash 包裹可执行、包内产物完备、
                  上游默认 /usr/share/ctronome 路径缺失时优雅退出、OSS /dev/dsp
                  缺失时优雅退出且 -d 覆盖生效、全部真实运行无崩溃

OHOS 说明：/system/bin/sh 不能直接 exec ELF，脚本一律由 bash 包裹调用。
两者均 fail closed：任何非零退出 / 超时即失败。
"""
import os
import shutil

from conan import ConanFile


class CtronomeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["ctronome"]
        bindir = os.path.join(dep.package_folder, "bin")
        binary = os.path.join(bindir, "ctronome")
        if not os.path.isfile(binary):
            raise FileNotFoundError(f"packaged ctronome not found: {binary}")

        # OHOS: /system/bin/sh 不能直接 exec ELF；必须用 bash 包裹脚本。
        # 解析顺序：CONFIG_SHELL（profile buildenv）→ PATH 查找 →
        # /data/service/hnp/bin/bash（OHOS 设备/worker 固定路径）；
        # 三者都拿不到则 fail closed（不允许跳过测试）。
        # 注意用 os.path.isfile 而非 os.access(X_OK)：HMDFS 上 chmod 会被忽略，
        # X_OK 恒为 False（R49/E046），会把可用 bash 误判为不可用。
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
            f'"{bash}" test.sh "{binary}"',
            env="conanrun",
            cwd=self.source_folder,
        )
        # 2) 鸿蒙特有测试（平台特性 + 平台能力缺口）
        self.run(
            f'"{bash}" test_ohos.sh "{binary}"',
            env="conanrun",
            cwd=self.source_folder,
        )
        self.output.info("ctronome: functional + OHOS tests OK (3 + 16 assertions)")
