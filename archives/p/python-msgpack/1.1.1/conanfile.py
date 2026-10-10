#!/usr/bin/env python3
"""Conan recipe for python-msgpack 1.1.1 — MessagePack serializer for Python.

Pure Python package (msgpack/ with automatic pure-Python fallback). The
upstream sdist also ships an optional C extension (_cmsgpack); this port
ships the pure-Python implementation (msgpack.fallback) — same public API
(Packer/Unpacker/packb/unpackb), no compilation step, no musl/clang risk.
It satisfies cachecontrol>=0.14's `msgpack>=0.5.2,<2.0.0` requirement.

NOTE: the conan package name is deliberately `python-msgpack` — the name
`msgpack` on ohpcd is already taken by msgpack-c 7.0.1 (the C library),
which does NOT provide the Python module.

R38 note: no console_scripts entry point, no bin/ payload — library only.
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get)


class PythonMsgpackConan(ConanFile):
    name = "python-msgpack"
    version = "1.1.1"
    package_type = "python-require"
    license = "Apache-2.0"
    homepage = "https://github.com/msgpack/msgpack-python"
    description = ("MessagePack serializer for Python (pure-Python "
                   "fallback; satisfies cachecontrol msgpack<2.0.0)")
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"

    # PyPI requires_dist: none (zero runtime dependencies; C extension
    # optional and not built in this port)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"]["python-msgpack"],
            strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        staging = os.path.join(self.build_folder, "msgpack-stage")
        shutil.rmtree(staging, ignore_errors=True)
        src_pkg = os.path.join(self.source_folder, "msgpack")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"msgpack package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(staging, "msgpack"),
            # drop the optional C-extension sources — pure-Python fallback
            # (msgpack/__init__.py: ImportError on _cmsgpack → .fallback)
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc",
                                          "_cmsgpack.c", "*.pyx"))

    def package(self):
        staging = os.path.join(self.build_folder, "msgpack-stage")
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copytree(
            os.path.join(staging, "msgpack"), os.path.join(site, "msgpack"),
            ignore=shutil.ignore_patterns("__pycache__"))
        src_lic = os.path.join(self.source_folder, "COPYING")
        if os.path.isfile(src_lic):
            lic_dir = os.path.join(self.package_folder, "licenses")
            os.makedirs(lic_dir, exist_ok=True)
            shutil.copy2(src_lic, os.path.join(lic_dir, "COPYING"))

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver,
                            "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
