#!/usr/bin/env python3
"""Conan recipe for aiohappyeyeballs 2.7.1 — pure Python library (setuptools).

HarmonyOS PC adaptation: Python package with src/ layout,
copies the aiohappyeyeballs package into site-packages for import.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AiohappyeyeballsConan(ConanFile):
    name = "aiohappyeyeballs"
    version = "2.7.1"
    description = "Happy Eyeballs Connector for aiohttp"
    license = "PSF-2.0"
    homepage = "https://github.com/aio-libs/aiohappyeyeballs"
    url = "https://github.com/aio-libs/aiohappyeyeballs"

    package_type = "python-require"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # src/ layout: package lives in src/aiohappyeyeballs after strip_root
        src_pkg = os.path.join(self.source_folder, "src", "aiohappyeyeballs")
        if not os.path.isdir(src_pkg):
            raise ConanException("aiohappyeyeballs package directory not found in source")
        # Run upstream pytest subset to report real pass rate
        # (manager review: upstream has tests/ suite, PR must not under-report)
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        tests_dir = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(tests_dir):
            self.output.warning("upstream tests/ not found, skipping pytest")
            return
        try:
            import subprocess
            res = subprocess.run(["python3", "-m", "pytest", "--version"],
                                 capture_output=True, timeout=30)
            if res.returncode != 0:
                self.output.warning("pytest unavailable, upstream tests skipped")
                return
        except Exception as e:
            self.output.warning(f"pytest unavailable, upstream tests skipped: {e}")
            return
        subset = ["test_impl.py", "test_init.py", "test_utils.py"]
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.join(self.source_folder, "src")
        try:
            res = subprocess.run(
                ["python3", "-m", "pytest", *subset, "-q", "--no-header",
                 "--tb=no", "--confcutdir", tests_dir],
                cwd=tests_dir, env=env, capture_output=True, timeout=180,
            )
            out = res.stdout.decode(errors="ignore").strip()
            self.output.info(f"upstream pytest subset: {out.splitlines()[-1] if out else 'n/a'}")
            if res.returncode != 0:
                self.output.warning("upstream pytest subset failed")
        except Exception as e:
            self.output.warning(f"upstream pytest run failed: {e}")

    def package(self):
        pkg_dir = os.path.join(self.package_folder, "lib", "python3.12", "site-packages", "aiohappyeyeballs")
        os.makedirs(pkg_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "src", "aiohappyeyeballs")
        for f in os.listdir(src):
            shutil.copy2(os.path.join(src, f), os.path.join(pkg_dir, f))

    def package_info(self):
        self.cpp_info.libs = []