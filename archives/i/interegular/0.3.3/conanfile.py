#!/usr/bin/env python3
"""Conan recipe for interegular 0.3.3 — pure Python regex intersection checker.

interegular is a regex intersection checker based on greenery. Pure Python
(noarch), no C/C++ compilation. No runtime dependencies.

Upstream tests: tests/test_comparator.py (pytest) + tests/test_patterns.py (unittest).
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class InteregularConan(ConanFile):
    name = "interegular"
    version = "0.3.3"
    description = "A regex intersection checker based on greenery"
    license = "MIT"
    homepage = "https://github.com/MegaIng/regex_intersections"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Pure Python noarch: settings required by CI L0 gate (same pattern as soupsieve)
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def build(self):
        apply_conandata_patches(self)

        python_exe = sys.executable
        src_dir = self.source_folder
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)

        # Build deps: setuptools + wheel
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 setuptools wheel',
        )

        # Install interegular into staging via --prefix (pure Python, no deps).
        # 清除 PIP_TARGET env var 避免与 --prefix 冲突
        import subprocess as _sp
        _env = dict(os.environ)
        _env.pop("PIP_TARGET", None)
        _r = _sp.run(
            [python_exe, "-m", "pip", "install", "--break-system-packages",
             "--no-deps", f"--prefix={staging}", src_dir],
            capture_output=True, text=True, env=_env, timeout=300)
        for _line in (_r.stdout or "").splitlines():
            self.output.info(_line)
        for _line in (_r.stderr or "").splitlines():
            self.output.info(_line)
        if _r.returncode != 0:
            raise Exception(f"pip install --prefix failed: returncode={_r.returncode}")

        # Install pytest (用同一清除后的 env)
        _r = _sp.run(
            [python_exe, "-m", "pip", "install", "--break-system-packages",
             "--timeout", "120", "pytest"],
            capture_output=True, text=True, env=_env, timeout=300)
        for _line in (_r.stdout or "").splitlines():
            self.output.info(_line)
        if _r.returncode != 0:
            raise Exception(f"pip install pytest failed: returncode={_r.returncode}")

        # ── 管理员规则 4：上游测试必须真实执行 ──
        _site_dst = os.path.join(staging, "lib", self._py_ver(), "site-packages")

        # 运行 unittest 测试（test_patterns.py）
        _result1 = self.run(
            f'PYTHONPATH="{_site_dst}:$PYTHONPATH" {python_exe} -m pytest '
            f'{os.path.join(src_dir, "tests", "test_patterns.py")} -v',
            ignore_errors=True)
        self.output.info(f"=== test_patterns.py returncode={_result1} ===")

        # 运行 pytest 测试（test_comparator.py）
        _result2 = self.run(
            f'PYTHONPATH="{_site_dst}:$PYTHONPATH" {python_exe} -m pytest '
            f'{os.path.join(src_dir, "tests", "test_comparator.py")} -v',
            ignore_errors=True)
        self.output.info(f"=== test_comparator.py returncode={_result2} ===")

        if _result1 != 0 or _result2 != 0:
            raise Exception(f"interegular upstream tests failed: "
                            f"test_patterns={_result1}, test_comparator={_result2}")

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        py_ver = self._py_ver()
        site_dst = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages"
        )
        bin_dst = os.path.join(self.package_folder, "bin")

        site_src = None
        for candidate in (
            os.path.join(staging, "lib", py_ver, "site-packages"),
            os.path.join(staging, "lib", py_ver, "dist-packages"),
            os.path.join(staging, "local", "lib", py_ver, "site-packages"),
            os.path.join(staging, "local", "lib", py_ver, "dist-packages"),
        ):
            if os.path.isdir(candidate) and os.path.isdir(
                os.path.join(candidate, "interegular")
            ):
                site_src = candidate
                break
        if site_src is None:
            raise Exception(
                f"interegular site-packages not found under staging={staging}"
            )

        copy(self, "*", src=site_src, dst=site_dst)

        for bin_src in (
            os.path.join(staging, "bin"),
            os.path.join(staging, "local", "bin"),
        ):
            if os.path.isdir(bin_src):
                copy(self, "*", src=bin_src, dst=bin_dst)

        for lic_name in ("LICENSE", "LICENSE.txt", "LICENSE.md"):
            src = os.path.join(self.source_folder, lic_name)
            if os.path.isfile(src):
                copy(
                    self,
                    lic_name,
                    src=self.source_folder,
                    dst=os.path.join(self.package_folder, "licenses"),
                )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []

        site_packages = os.path.join(
            self.package_folder, "lib", self._py_ver(), "site-packages"
        )
        self.runenv_info.append_path("PYTHONPATH", site_packages)
        self.buildenv_info.append_path("PYTHONPATH", site_packages)
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)