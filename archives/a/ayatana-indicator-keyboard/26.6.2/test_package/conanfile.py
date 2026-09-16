#!/usr/bin/env python3
"""Conan test_package — ayatana-indicator-keyboard 26.6.2

R34/PF3: test() 必须实质运行被测包。本包主产物是 D-Bus 服务可执行文件
ayatana-indicator-keyboard-service（无对外库 API），因此测试直接运行该
可执行文件：--version 断言输出含版本号，--help 验证 CLI 可用。

注：服务主体需要会话 D-Bus + GSettings schema + X11 显示，纯 CI/容器无法
完整拉起，--version/--help 走 main() 前置分支（0002 补丁），不触达服务初始化。

机器证据（HMBS 真机门禁硬要求）：
- HMBS_TEST_PACKAGE_RESULT：discovered=2/passedCount=2（两条真实 grep 断言）。
- HMBS_UPSTREAM_TEST_RESULT：status=no_tests（上游确无测试，审计见 MANIFEST.yml）。
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class AyatanaIndicatorKeyboardTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["ayatana-indicator-keyboard"]
        service = os.path.join(pkg.package_folder, "bin", "ayatana-indicator-keyboard-service")
        if not os.path.isfile(service):
            raise ConanException(f"missing packaged executable: {service}")

        marker = {
            "executed": True,
            "passed": True,
            "command": '"ayatana-indicator-keyboard-service" --version/--help smoke (2 assertions)',
            "discovered": 2,
            "passedCount": 2,
        }
        try:
            # Smoke 1: --version 必须输出 "ayatana-indicator-keyboard 26.6.2" 且 rc=0。
            # self.run 返回 int 退出码，非零即抛 ConanException；断言内嵌在 shell 管道中。
            self.run(
                f'"{service}" --version 2>&1 | grep -q "ayatana-indicator-keyboard 26.6.2"',
                env="conanrun",
            )
            # Smoke 2: --help 必须 rc=0 且包含 Usage 行。
            self.run(f'"{service}" --help 2>&1 | grep -q "Usage:"', env="conanrun")
        except Exception:
            marker["passed"] = False
            marker["passedCount"] = 0
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
            raise

        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))

        # 上游确无测试（审计见 test_package/MANIFEST.yml）：每轮必跑的 test() 中
        # 复发该标记——主配方 build() 的输出在包缓存命中轮次不会出现。
        upstream_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "no upstream test target (see test_package/MANIFEST.yml audit)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "ayatana-indicator-keyboard 26.6.2 上游确无测试：源码包无 tests/ "
                "目录；顶层与 src/CMakeLists.txt 无 enable_testing/include(CTest)/"
                "add_test/add_subdirectory(tests) 接线；INSTALL.md 的 gtest 提及为"
                "未接线的陈旧文档（同族 session 上游亦然）"
            ),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False))
        self.output.info("ayatana-indicator-keyboard-service 26.6.2 smoke OK")
