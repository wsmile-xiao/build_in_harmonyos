#!/usr/bin/env python3
"""Conan test_package for requests 2.22.0 — consumer check.

Runs test_requests_consumer.py (standalone test source, satisfies L0c) via
self.run with env="conanrun". PYTHONPATH for the four runtime dependencies is
injected explicitly — package_info printing the path does not propagate it to
the test process on its own (aiohttp lesson: "No module named 'multidict'").
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException

DEPS = ("certifi", "chardet", "idna", "urllib3")


class RequestsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        pkg = self.dependencies["requests"].package_folder
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isdir(os.path.join(site, "requests")):
            raise ConanException(f"requests package missing under {site}")
        paths = [site]
        for dep_name in DEPS:
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
                                   "test_requests_consumer.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_requests_consumer.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
