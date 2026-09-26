#!/usr/bin/env python3
"""Conan test_package — xdms 1.3.2 consumer verification.

Exercises the packaged CLI the way a real consumer would: usage screen, archive
integrity test, metadata view, and a genuine DMS decode whose output bytes are
compared against independently regenerated expected data.  Also asserts the
failure paths (non-DMS input, corrupted payload CRC) exit non-zero.

Upstream ships no test suite (upstream_total = 0, see MANIFEST.yml), so this is
consumer verification — it is NOT counted as upstream tests.
"""
import os
import shutil

from conan import ConanFile


class XdmsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = (os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                or "/data/service/hnp/bin/bash")
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_xdms.sh")
        self.run(f'{bash} {script} "{os.path.join(pkg_folder, "bin")}"',
                 env="conanrun")
