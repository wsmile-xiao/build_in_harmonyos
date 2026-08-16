#!/usr/bin/env python3
"""Conan recipe for aiosignal 1.4.0 — pure Python library (setuptools).

HarmonyOS PC adaptation: Python package at top level (aiosignal/),
copies the aiosignal package into site-packages for import.
Requires frozenlist (published in main).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AiosignalConan(ConanFile):
    name = "aiosignal"
    version = "1.4.0"
    description = "aiosignal: a list of registered asynchronous callbacks"
    license = "Apache-2.0"
    homepage = "https://github.com/aio-libs/aiosignal"
    url = "https://github.com/aio-libs/aiosignal"

    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("frozenlist/1.8.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isdir(os.path.join(self.source_folder, "aiosignal")):
            raise ConanException("aiosignal package directory not found in source")
        # Run upstream pytest subset to report real pass rate
        # (manager review: upstream has tests/ suite, PR must not under-report)
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        tests_dir = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(tests_dir):
            self.output.warning("upstream tests/ not found, skipping pytest")
            return
        import subprocess
        # CI worker 的 PATH 可能不含 python3，用绝对路径定位（本机
        # python3 位于 /storage/Users/currentUser/usr/local/bin/python3）
        python = self._find_python()
        if not python:
            self.output.warning("python3 not found, upstream tests skipped")
            return
        try:
            res = subprocess.run([python, "-m", "pytest", "--version"],
                                 capture_output=True, timeout=30)
            if res.returncode != 0:
                self.output.warning("pytest unavailable, upstream tests skipped")
                return
        except Exception as e:
            self.output.warning(f"pytest unavailable, upstream tests skipped: {e}")
            return
        # aiosignal imports frozenlist at module load — add its site-packages
        paths = [self.source_folder]
        if "frozenlist" in self.dependencies:
            fl_site = os.path.join(
                self.dependencies["frozenlist"].package_folder,
                "lib", "python3.12", "site-packages")
            if os.path.isdir(fl_site):
                paths.append(fl_site)
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(paths)
        subset = ["test_signals.py"]
        try:
            res = subprocess.run(
                [python, "-m", "pytest", *subset, "-q", "--no-header",
                 "--tb=no", "-o", "addopts=", "--confcutdir", tests_dir],
                cwd=tests_dir, env=env, capture_output=True, timeout=180,
            )
            out = res.stdout.decode(errors="ignore").strip()
            self.output.info(f"upstream pytest subset: {out.splitlines()[-1] if out else 'n/a'}")
            if res.returncode != 0:
                self.output.warning("upstream pytest subset failed")
        except Exception as e:
            self.output.warning(f"upstream pytest run failed: {e}")

    def _find_python(self):
        import shutil
        candidates = [
            "/storage/Users/currentUser/usr/local/bin/python3",
            "/usr/bin/python3",
            "/system/bin/python3",
            shutil.which("python3") or "",
        ]
        return next((p for p in candidates if p and os.path.isfile(p)), "")

    def package(self):
        pkg_dir = os.path.join(self.package_folder, "lib", "python3.12", "site-packages", "aiosignal")
        os.makedirs(pkg_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "aiosignal")
        for f in os.listdir(src):
            fpath = os.path.join(src, f)
            if os.path.isdir(fpath):
                continue
            shutil.copy2(fpath, os.path.join(pkg_dir, f))

    def package_info(self):
        self.cpp_info.libs = []