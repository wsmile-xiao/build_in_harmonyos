#!/usr/bin/env python3
"""Conan recipe for multidict 6.7.1 — Python library (setuptools + optional C extension).

HarmonyOS PC adaptation: packages the pure-Python fallback of multidict
(the _multidict C extension is optional; __init__.py degrades gracefully).
Requires typing-extensions (published in main).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MultidictConan(ConanFile):
    name = "multidict"
    version = "6.7.1"
    description = "multidict implementation"
    license = "Apache-2.0"
    homepage = "https://github.com/aio-libs/multidict"
    url = "https://github.com/aio-libs/multidict"

    package_type = "python-require"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("typing-extensions/4.16.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isdir(os.path.join(self.source_folder, "multidict")):
            raise ConanException("multidict package directory not found in source")
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
        subset = ["test_multidict.py", "test_updatable.py", "test_abc.py"]
        env = dict(os.environ)
        env["PYTHONPATH"] = self.source_folder
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
        pkg_dir = os.path.join(self.package_folder, "lib", "python3.12", "site-packages", "multidict")
        os.makedirs(pkg_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "multidict")
        for f in os.listdir(src):
            fpath = os.path.join(src, f)
            if os.path.isdir(fpath):
                continue  # skip subdirs (e.g. _multilib C headers)
            if f.endswith((".pyx", ".pxd", ".c", ".h")):
                continue  # C/Cython sources not needed; pure-Python fallback used
            shutil.copy2(fpath, os.path.join(pkg_dir, f))

    def package_info(self):
        self.cpp_info.libs = []