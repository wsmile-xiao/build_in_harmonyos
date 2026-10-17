#!/usr/bin/env python3
"""Conan test_package — rst-lint 2.0.2 consumer verification (R34).

The test really consumes the packaged artifact:
  * imports the *installed* `restructuredtext_lint` API (version + lint)
  * executes the generated `bin/rst-lint` console script end-to-end

Every declared dependency's site-packages is placed on PYTHONPATH so that
`import docutils` resolves through the packaged `docutils/0.23` requirement
(catkin-pkg / awscli precedent). The distinction between upstream tests and
test_package tests is recorded in test_package/MANIFEST.yml.
"""
import os
import subprocess
import sys

from conan import ConanFile
from conan.tools.build import can_run


class RstLintTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("docutils/0.23")

    def test(self):
        if not can_run(self):
            return
        env = os.environ.copy()
        site_packages = []
        candidates = (
            os.path.join("lib", "site-packages"),
            os.path.join("lib", "python3.12", "site-packages"),
            os.path.join("lib", "python{0}.{1}".format(
                sys.version_info.major, sys.version_info.minor), "site-packages"),
            os.path.join("lib", "python", "site-packages"),
        )
        for package in self.dependencies.values():
            if not package.package_folder:
                continue
            for relative_path in candidates:
                path = os.path.join(package.package_folder, relative_path)
                if os.path.isdir(path) and path not in site_packages:
                    site_packages.append(path)
        env["PYTHONPATH"] = os.pathsep.join(
            site_packages + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))

        pkg = self.dependencies["rst-lint"].package_folder
        cli = os.path.join(pkg, "bin", "rst-lint")
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "test_rst_lint.py")
        command = [sys.executable, script, cli]
        if os.environ.get("OHC_USE_CONAN_RUN") == "1":
            self.run(" ".join('"{0}"'.format(value) for value in command),
                     env="conanrun")
        else:
            subprocess.check_call(command, env=env)
