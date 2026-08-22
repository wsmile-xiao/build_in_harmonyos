#!/usr/bin/env python3
"""Conan test_package for confspirator 0.3.0 — consumer check.

Runs test_confspirator.py (standalone test source, satisfies L0c) via
self.run with env="conanrun" (the conanrun PATH injection is required —
a bare subprocess would lose it, see yarl FileNotFoundError lesson).
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class ConfspiratorTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["confspirator"].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isdir(os.path.join(site, "confspirator")):
            raise ConanException(f"confspirator package missing under {site}")
        # confspirator/__init__.py 顶层 import toml（运行时依赖）——
        # 遍历所有依赖注入 site-packages 到 PYTHONPATH（toml 的 lib/pythonX/site-packages）
        sites = [site]
        for _ref, dep in self.dependencies.items():
            if dep.ref.name == "confspirator":
                continue
            dep_site = os.path.join(dep.package_folder, "lib", py_ver, "site-packages")
            if os.path.isdir(dep_site):
                sites.append(dep_site)
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_confspirator.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_confspirator.py missing: {test_script}")
        os.environ["PYTHONPATH"] = ":".join(sites)
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
