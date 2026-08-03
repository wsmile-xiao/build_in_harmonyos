#!/usr/bin/env python3
"""Conan test_package — rbenv-bundle-exec 1.0.0 smoke test

Delegates shell-level checks (file existence + bash syntax) to test.sh,
following the project convention used by chruby, anyenv, and other packages.
On platforms without bash (e.g., Windows CI), falls back to Python file
existence checks to ensure LICENSE and hook script are verified.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class RbenvBundleExecTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # P3 fix: rbenv-bundle-exec 是纯 Bash 脚本,通过 host 的 bash 解释器执行,
        # 不需要 target 二进制。can_run() 在交叉编译时返回 False 会静默跳过测试,
        # 对纯脚本包过度保守。改用 cross_building() 仅在真正交叉编译时跳过
        # (host 无 bash 解释器的情况,如 Windows CI,已在下方用 shutil.which 处理)。
        if cross_building(self):
            self.output.info("Cross-building detected; skipping test")
            return

        dep = self.dependencies["rbenv-bundle-exec"]
        plugin_dir = os.path.join(dep.package_folder, "share", "rbenv-bundle-exec")
        plugin_bash = os.path.join(plugin_dir, "etc", "rbenv.d", "exec", "bundle-exec.bash")

        bash_path = shutil.which("bash")
        if bash_path:
            # 调用 test.sh 执行完整的 shell 层面测试
            self.run(
                f'cd "{self.source_folder}" && '
                f'"{bash_path}" test.sh "{plugin_dir}"',
                env="conanrun"
            )
        else:
            # Windows 无 bash 时回退到 Python 文件存在性检查
            self.output.warning("bash not found; falling back to Python file existence check")
            if not os.path.isdir(plugin_dir):
                raise Exception(f"Missing plugin directory: {plugin_dir}")
            if not os.path.isfile(plugin_bash):
                raise Exception(f"Missing plugin bash file: {plugin_bash}")
            license_path = os.path.join(plugin_dir, "LICENSE")
            if not os.path.isfile(license_path):
                raise Exception(f"Missing LICENSE file: {license_path}")
            self.output.info("File existence check passed (bash not available for syntax check)")
