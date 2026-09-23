#!/usr/bin/env python3
"""Conan test_package for ayatana-indicator-notifications — R34 real binary smoke test.

L1 official test: 定位包内实际安装的服务可执行文件
`ayatana-indicator-notifications-service`，通过 self.run() 执行 test.sh，
后者对二进制做 --version/--help 冒烟校验，并断言 --version 输出含版本号
23.10.1。

- R34: 真实执行被测包二进制（非空壳，非仅打印字符串）。
- L0d: test() 使用 self.run() 调用被测包二进制。
- 运行库路径：VirtualRunEnv 的 conanrun 仅聚合声明了 run env 的依赖，
  generate() 显式遍历整张依赖图收集全部 lib 目录，写入自定义 env 脚本
  conanrun_test，供 self.run(env="conanrun_test") 加载（与 libayatana-common
  配方同思路）。
- OHOS 上 D-Bus session service 无法在无 session bus 环境下常驻，
  --version/--help 是 main.c 补丁新增的 CLI 分支（见 patches/0003）。
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        """构造 conanrun_test 环境：全部依赖 lib 目录 -> LD_LIBRARY_PATH。"""
        env = Environment()
        lib_dirs = self._collect_lib_dirs()
        env.define_path("LD_LIBRARY_PATH", lib_dirs)
        env.vars(self).save_script("conanrun_test")

    def test(self):
        if not can_run(self):
            self.output.warning("无法运行被测二进制，跳过 smoke test")
            return

        pkg = self.dependencies["ayatana-indicator-notifications"].package_folder
        binary = self._find_binary(pkg)
        if not binary:
            self.output.error(f"未找到服务二进制 (pkg={pkg})")
            sys.exit(1)

        self.output.info(f"被测二进制: {binary}")

        # R34/L0d: 真实执行被测包二进制（非空壳）。
        # test.sh 负责 --version/--help 与版本号断言，失败即非零退出。
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.sh")
        rc = self.run(f'sh "{script}" "{binary}"', env="conanrun_test", ignore_errors=True)
        if rc != 0:
            self.output.error(f"smoke test 失败 (self.run 退出码 {rc})")
            sys.exit(1)

        self.output.info("✅ smoke test 通过：服务二进制可执行且输出正确版本")

    # ── helpers ──────────────────────────────────────────────

    def _collect_lib_dirs(self):
        lib_dirs = []
        for dep in self.dependencies.values():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            for libdir in getattr(dep.cpp_info, "libdirs", None) or ["lib"]:
                path = os.path.join(folder, libdir)
                if os.path.isdir(path) and path not in lib_dirs:
                    lib_dirs.append(path)
        return lib_dirs

    def _find_binary(self, pkg):
        # 上游 CMake 把服务装到 libexec/ayatana-indicator-notifications/ 下
        candidates = [
            os.path.join(pkg, "libexec", "ayatana-indicator-notifications",
                         "ayatana-indicator-notifications-service"),
            os.path.join(pkg, "libexec", "ayatana-indicator-notifications-service"),
            os.path.join(pkg, "bin", "ayatana-indicator-notifications",
                         "ayatana-indicator-notifications-service"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        # 递归兜底
        for root, _dirs, files in os.walk(pkg):
            if "ayatana-indicator-notifications-service" in files:
                return os.path.join(root, "ayatana-indicator-notifications-service")
        return None
