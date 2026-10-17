#!/usr/bin/env python3
"""Conan recipe for sgmllib3k 1.0.0 — SGML parser (Python 3 port).

Pure Python single module (sgmllib.py), zero runtime dependencies (stdlib
only). It is the runtime dependency of feedparser 6.0.x (HTML/XML feed
sanitizing path). HarmonyOS PC adaptation: copytree staging (appdirs
single-module pattern) — the module only uses re/string/io from the stdlib,
so nothing breaks on the platform's Python 3.12. No source patch required.

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


class Sgmllib3kConan(ConanFile):
    name = "sgmllib3k"
    version = "1.0.0"
    package_type = "python-require"
    license = "BSD"  # upstream setup.py: "License :: OSI Approved :: BSD License"
    homepage = "https://pypi.org/project/sgmllib3k/"
    description = "Python 3 port of the stdlib SGML parser module (feedparser dependency)"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"

    # PyPI requires_dist: none (zero runtime dependencies, stdlib only)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"]["sgmllib3k"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        staging = os.path.join(self.build_folder, "sgmllib3k-stage")
        shutil.rmtree(staging, ignore_errors=True)
        src_mod = os.path.join(self.source_folder, "sgmllib.py")
        if not os.path.isfile(src_mod):
            raise ConanException(f"sgmllib.py module missing: {src_mod}")
        os.makedirs(staging, exist_ok=True)
        shutil.copy2(src_mod, os.path.join(staging, "sgmllib.py"))

    def package(self):
        staging = os.path.join(self.build_folder, "sgmllib3k-stage")
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        dst = os.path.join(site, "sgmllib.py")
        shutil.copy2(os.path.join(staging, "sgmllib.py"), dst)
        if not os.path.isfile(dst):
            raise ConanException(f"sgmllib.py missing under {dst}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver,
                            "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
