#!/usr/bin/env python3
"""Conan test_package for libervia-templates 0.9.0-hg413 — consumer check.

Runs test_libervia_templates.py (standalone test source, satisfies L0c) via
self.run with env="conanrun". PYTHONPATH for the packaged sat_templates and the
jinja2 dependency is injected explicitly (jinja2/aiohttp lesson: package_info
printing PYTHONPATH does not propagate it to the test process on its own).
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class LiberviaTemplatesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        pkg = self.dependencies["libervia-templates"].package_folder
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isdir(os.path.join(site, "sat_templates")):
            raise ConanException(
                f"sat_templates package missing under {site}")
        paths = [site]
        for dep_name in ("jinja2",):
            dep = self.dependencies.get(dep_name)
            if dep is None:
                raise ConanException(f"missing dependency: {dep_name}")
            dsite = os.path.join(dep.package_folder, "lib", py_ver,
                                 "site-packages")
            if not os.path.isdir(dsite):
                raise ConanException(f"{dep_name} site-packages missing: {dsite}")
            paths.append(dsite)
        os.environ["PYTHONPATH"] = os.pathsep.join(paths)

        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_libervia_templates.py")
        if not os.path.isfile(test_script):
            raise ConanException(
                f"test_libervia_templates.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")

        # 鸿蒙特有测试：端到端消费者用例（完整页面渲染 + 产物落盘 + 校验）
        e2e_script = os.path.join(os.path.dirname(__file__),
                                  "test_consumer_e2e.py")
        if not os.path.isfile(e2e_script):
            raise ConanException(f"test_consumer_e2e.py missing: {e2e_script}")
        self.run(f"python3 '{e2e_script}' '{site}'", env="conanrun")
