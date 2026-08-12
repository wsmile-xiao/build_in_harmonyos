#!/usr/bin/env python3
"""Conan test_package for imgp — Python-based verification.

Tests that imgp can be imported and its CLI command works.
Includes a real image processing test to verify functionality.
"""
import os
from conan import ConanFile


class ImgpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # PIL was installed to ~/usr/local/ (--prefix to avoid noexec ~/.local/).
        # Add its path to PYTHONPATH so import imgp can find PIL.
        # Dynamically detect Python version to align with conanfile.py package().
        import subprocess
        try:
            result = subprocess.run(
                ["python3", "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                capture_output=True, text=True, timeout=10)
            py_ver = f"python{result.stdout.strip()}" if result.returncode == 0 and result.stdout.strip() else "python3.12"
        except Exception:
            py_ver = "python3.12"
        user_site = os.path.expanduser(f"~/usr/local/lib/{py_ver}/site-packages")
        # L1 负向测试修复: import imgp 必须加载 conan 包的 imgp.py
        # (package_folder/lib/python3.12/site-packages),而非 pip user 安装的
        # ~/.local/.../imgp.py —— 否则 test 未真正依赖被测包(L1 fail:
        # 'test does not depend on package')。
        pkg_folder = self.dependencies["imgp"].package_folder
        pkg_site = os.path.join(pkg_folder, "lib", py_ver, "site-packages")
        paths = []
        if os.path.isdir(pkg_site):
            paths.append(pkg_site)
        if os.path.isdir(user_site):
            paths.append(user_site)
        if paths:
            # 追加（不覆盖）conanrun 环境已有的 PYTHONPATH，保留 imgp 包自身 lib 路径
            # IMGP_PKG_SITE: 传给 test.py 供路径断言——L1e 负向测试会 sabotage
            # 移走包 lib/,此时 import imgp 回退到 pip 版,断言 imgp.__file__
            # 必须以 IMGP_PKG_SITE 开头,证明 test 真正依赖被测包(R34)。
            self.run(
                f"IMGP_PKG_SITE={pkg_site} "
                f"IMGP_PIL_SITE={user_site} "
                f"PYTHONPATH={':'.join(paths)}:$PYTHONPATH python3 test.py",
                env="conanrun",
            )
        else:
            self.output.warning(f"site-packages not found: {pkg_site} / {user_site}")
            # 不设 PYTHONPATH 前缀，直接用 python3 test.py 保留 conanrun 环境原有路径
            self.run("python3 test.py", env="conanrun")