#!/usr/bin/env python3
"""Conan consumer test for the packaged catkin-pkg Python API."""

import os
import subprocess
import sys

from conan import ConanFile

class CatkinPkgTestConan(ConanFile):
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("docutils/0.23")
        self.requires("packaging/26.3")
        self.requires("python-dateutil/2.9.0.post0")
        self.requires("pyparsing/3.1.4")

    def test(self):
        env = os.environ.copy()
        site_packages = []
        for package in self.dependencies.values():
            for relative_path in (
                os.path.join("lib", "site-packages"),
                os.path.join("lib", "python3.12", "site-packages"),
                os.path.join("lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"),
            ):
                path = os.path.join(package.package_folder, relative_path)
                if os.path.isdir(path) and path not in site_packages:
                    site_packages.append(path)
        env["PYTHONPATH"] = os.pathsep.join(
            site_packages + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
        )
        command = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "test_consumer.py"),
        ]
        if os.environ.get("OHC_USE_CONAN_RUN") == "1":
            self.run(" ".join(f'\"{value}\"' for value in command), env="conanrun")
        else:
            subprocess.check_call(command, env=env)
