#!/usr/bin/env python3
"""Conan test_package for advai-cli — Python-based verification."""
import os
from conan import ConanFile


class AdvaiCliTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        import subprocess
        try:
            result = subprocess.run(
                ["python3", "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                capture_output=True, text=True, timeout=10)
            py_ver = f"python{result.stdout.strip()}" if result.returncode == 0 and result.stdout.strip() else "python3.12"
        except Exception:
            py_ver = "python3.12"
        user_site = os.path.expanduser(f"~/usr/local/lib/{py_ver}/site-packages")
        pkg_folder = self.dependencies["advai-cli"].package_folder
        pkg_site = os.path.join(pkg_folder, "lib", py_ver, "site-packages")
        # 包内 bin 目录(含 advai CLI 脚本)——test.py 用它做绝对路径调用,
        # 避免 CI 沙箱中裸命令 "advai" 找不到(pip 装到 ~/.local/bin 不可访问)。
        pkg_bin = os.path.join(pkg_folder, "bin")
        paths = []
        if os.path.isdir(pkg_site):
            paths.append(pkg_site)
        if os.path.isdir(user_site):
            paths.append(user_site)
        if paths:
            self.run(
                f"ADVAI_PKG_SITE={pkg_site} "
                f"ADVAI_DEPS_SITE={user_site} "
                f"ADVAI_PKG_BIN={pkg_bin} "
                f"PYTHONPATH={':'.join(paths)}:$PYTHONPATH python3 test.py",
                env="conanrun",
            )
        else:
            self.output.warning(f"site-packages not found: {pkg_site} / {user_site}")
            self.run("python3 test.py", env="conanrun")
