#!/usr/bin/env python3
"""test_package for dh-shell-completions 0.1.0 — 脚本/application 包消费者测试。

上游测试（tests/run.sh gen|composite|separate）已在配方 build() 内真实执行；
此处以消费者视角断言包产物（Debian 安装布局 + 核心内容标记），
由 test.sh 落地（L1e：CI 会先删除包 bin/ 再重跑本测试，
断言必须读取包内产物以保证破坏后失败）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class DhShellCompletionsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        dep = self.dependencies["dh-shell-completions"]
        pkg_dir = dep.package_folder

        candidates = []
        if dep.cpp_info.bindirs:
            candidates += [os.path.join(pkg_dir, d) for d in dep.cpp_info.bindirs]
        candidates.append(os.path.join(pkg_dir, "bin"))
        bin_dir = next((p for p in candidates if os.path.isdir(p)), None)
        if bin_dir is None:
            raise ConanException(
                f"dh-shell-completions package has no bin/ directory under {pkg_dir}; "
                "package() may have failed to install dh_shell_completions"
            )

        self.run(f"{bash} test.sh {bin_dir} {pkg_dir}", env="conanrun")
