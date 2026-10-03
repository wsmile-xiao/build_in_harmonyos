import os
import shutil

from conan import ConanFile


class J4DmenuTestConan(ConanFile):
    """test_package for the j4-dmenu-desktop executable.

    Runs three layers of consumer-side testing against the *installed* product:
      1. test.sh      — 冒烟：--version / --help 基本可执行性
      2. test_e2e.sh  — 完整消费者用例（端到端）：真实 XDG 环境 + 伪 dmenu 协议，
                        驱动 扫描→解析→过滤→候选列表→选择→execvp 全链路
      3. test_ohos.sh — 鸿蒙（OpenHarmony PC / aarch64）平台特有断言
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["j4-dmenu"]
        binary = os.path.join(dep.package_folder, "bin", "j4-dmenu-desktop")
        if not os.path.isfile(binary):
            raise FileNotFoundError(f"packaged j4-dmenu-desktop not found: {binary}")

        # OHOS: /system/bin/sh 不能直接 exec ELF；必须用 bash 包裹脚本。
        # 解析顺序：CONFIG_SHELL（profile buildenv）→ PATH 查找 →
        # /data/service/hnp/bin/bash（OHOS 设备/worker 固定路径）；
        # 三者都拿不到则 fail closed（不允许跳过测试）。
        # 注意用 os.path.isfile 而非 os.access(X_OK)：HMDFS 上 chmod 会被忽略，
        # X_OK 恒为 False，会把可用 bash 误判为不可用。
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

        # 1) 冒烟测试（--version / --help）
        self.run(f'"{bash}" test.sh', env="conanrun", cwd=self.source_folder)
        # 2) 完整消费者用例（端到端，真实启动目标程序）
        self.run(
            f'"{bash}" test_e2e.sh "{binary}"',
            env="conanrun",
            cwd=self.source_folder,
        )
        # 3) 鸿蒙平台特有测试（产物形态 + 平台约束行为）
        self.run(
            f'"{bash}" test_ohos.sh "{binary}"',
            env="conanrun",
            cwd=self.source_folder,
        )
        self.output.info(
            "j4-dmenu: smoke + e2e consumer + OHOS platform tests OK"
        )
