#!/usr/bin/env python3
"""Conan test_package — webbench 1.5 consumer verification.

Runs the packaged CLI against a local loopback HTTP server (started by the test
script) and checks the version/usage/connect-failure paths plus the benchmark
report.  Upstream ships no test suite (upstream_total = 0, see MANIFEST.yml),
so this is consumer verification — it is NOT counted as upstream tests.
"""
import os
import shutil

from conan import ConanFile


class WebbenchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = (os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                or "/data/service/hnp/bin/bash")
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_webbench.sh")
        self.run(f'{bash} {script} "{os.path.join(pkg_folder, "bin")}"',
                 env="conanrun")
