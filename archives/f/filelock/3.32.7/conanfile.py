#!/usr/bin/env python3
"""Conan recipe for filelock 3.32.7 — platform-independent file locking.

Pure Python (src/filelock), zero runtime dependencies (stdlib only).
HarmonyOS PC adaptation: copytree staging (awscli WR-008 pattern) — no pip
build step needed; the module only uses os/sys/pathlib/threading from the
stdlib, so nothing breaks on the platform's Python 3.12. Upstream supports
Safari-ish platform quirks via os.fsync guards; no source patch required.

R38 note: no console_scripts entry point, no bin/ payload — library only,
hence no commands.json and no cpp_info.bindirs declaration.
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get)


class FilelockConan(ConanFile):
    name = "filelock"
    version = "3.32.7"
    package_type = "python-require"
    license = "MIT"
    homepage = "https://github.com/tox-dev/py-filelock"
    description = "A platform-independent file lock for Python"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"

    # PyPI requires_dist: none (zero runtime dependencies, stdlib only)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"]["filelock"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # pip metadata builds are unreliable in CI — copytree source to a
        # staging dir under self.build_folder (WR-008; pure Python, no
        # compilation)
        staging = os.path.join(self.build_folder, "filelock-stage")
        shutil.rmtree(staging, ignore_errors=True)
        src_pkg = os.path.join(self.source_folder, "src", "filelock")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"filelock package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(staging, "filelock"),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def package(self):
        staging = os.path.join(self.build_folder, "filelock-stage")
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copytree(
            os.path.join(staging, "filelock"), os.path.join(site, "filelock"),
            ignore=shutil.ignore_patterns("__pycache__"))
        lic_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(lic_dir, exist_ok=True)
        for lic in ("LICENSE", "LICENSE.txt"):
            src = os.path.join(self.source_folder, lic)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(lic_dir, lic))
                break

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver,
                            "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
