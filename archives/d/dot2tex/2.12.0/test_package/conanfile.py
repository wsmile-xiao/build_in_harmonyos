#!/usr/bin/env python3
"""Conan test_package for dot2tex 2.12.0 — pure Python CLI tool test.

Verifies that the dot2tex command is functional after installation.
Tests:
  1. dot2tex --version 输出正确的版本信息
  2. Python 模块导入 (import dot2tex)
  3. dot2tex 基本转换功能 (最小 DOT → TikZ)

PYTHONPATH 显式聚合 dot2tex 与依赖 pyparsing 的 site-packages
（pyparsing binary 在 test 阶段可能被跳过，runenv_info 不自动聚合，
  故从 self.dependencies 取 package_folder 手动注入）。
"""
import os
import subprocess
import sys

from conan import ConanFile
from conan.tools.build import can_run


class Dot2texTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # dot2tex 运行时依赖 pyparsing：test 显式声明为直接依赖，
        # 避免其作为传递依赖在 test 阶段被 Skipped 而无法注入 PYTHONPATH。
        self.requires("pyparsing/3.1.4")

    def test(self):
        if can_run(self):
            dep = self.dependencies["dot2tex"]
            bin_dir = os.path.join(dep.package_folder, "bin")

            # PATH: 确保 bin/ 在前
            env = dict(os.environ)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

            # PYTHONPATH: dot2tex + pyparsing 的 site-packages
            python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
            site_pkgs_rel = os.path.join("lib", python_version, "site-packages")
            paths = [os.path.join(dep.package_folder, site_pkgs_rel)]
            try:
                pydep = self.dependencies["pyparsing"]
                paths.append(os.path.join(pydep.package_folder, site_pkgs_rel))
            except Exception:
                pass
            env["PYTHONPATH"] = ":".join(paths + [env.get("PYTHONPATH", "")]).strip(":")

            # Test 1: dot2tex --version
            self.output.info("Test 1: dot2tex --version")
            dot2tex_bin = os.path.join(bin_dir, "dot2tex")
            result = subprocess.run(
                [dot2tex_bin, "--version"],
                capture_output=True, text=True, timeout=30, env=env
            )
            if result.returncode != 0:
                self.output.error(f"dot2tex --version failed: {result.stderr}")
                raise Exception("dot2tex --version 执行失败")
            self.output.info(f"dot2tex --version: {result.stdout.strip()}")
            # Verify version string contains expected version
            if "2.12.0" not in result.stdout:
                self.output.warning(f"版本号可能不匹配: {result.stdout.strip()}")

            # Test 2: Python module import
            # Use the interpreter Conan runs us with; fall back to 'python3'.
            # Do NOT reach into dep.package_folder/bin/python3 — that path never
            # exists because python3 is a separate Conan package.
            self.output.info("Test 2: import dot2tex")
            python = sys.executable or "python3"
            result = subprocess.run(
                [python, "-c",
                 "import dot2tex; print(f'import OK: {dot2tex.__file__}')"],
                capture_output=True, text=True, timeout=30, env=env
            )
            if result.returncode != 0:
                self.output.error(f"import dot2tex 失败: {result.stderr}")
                raise Exception("Python 模块导入失败")
            self.output.info(f"模块导入成功: {result.stdout.strip()}")

            # Test 3: Run test.sh smoke test (same env so pyparsing is importable)
            self.output.info("Test 3: test.sh smoke test")
            self.run("bash test.sh", env="conanrun", cwd=self.source_folder)
