#!/usr/bin/env python3
"""Conan test_package for pgpdump 0.37."""
import os
import shutil

from conan import ConanFile


class PgpdumpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_pgpdump.sh")
        self.run(f'{bash} {script} ./bin/pgpdump', env="conanrun", cwd=pkg_folder)
