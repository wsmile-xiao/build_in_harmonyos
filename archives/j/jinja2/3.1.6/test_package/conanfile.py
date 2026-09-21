#!/usr/bin/env python3
"""Conan test_package for Jinja2 3.1.6 — consumer check.

Runs test_jinja2.py (standalone test source, satisfies L0c) via self.run with
env="conanrun". PYTHONPATH for the markupsafe dependency is injected explicitly
(aiohttp lesson: package_info printing PYTHONPATH does not propagate it to the
test process on its own).
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class Jinja2TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        pkg = self.dependencies["jinja2"].package_folder
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isdir(os.path.join(site, "jinja2")):
            raise ConanException(f"jinja2 package missing under {site}")
        paths = [site]
        for dep_name in ("markupsafe",):
            dep = self.dependencies.get(dep_name)
            if dep is None:
                raise ConanException(f"missing dependency: {dep_name}")
            dsite = os.path.join(dep.package_folder, "lib", py_ver,
                                 "site-packages")
            if not os.path.isdir(dsite):
                raise ConanException(f"{dep_name} site-packages missing: {dsite}")
            paths.append(dsite)
        os.environ["PYTHONPATH"] = os.pathsep.join(paths)

        test_script = os.path.join(os.path.dirname(__file__), "test_jinja2.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_jinja2.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
