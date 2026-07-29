#!/usr/bin/env python3
"""Conan test_package - osmctools 0.9

R34: test_package must substantially exercise the tested package's functionality.
osmctools is a CLI binary package (osmconvert/osmfilter/osmupdate), so tests run
the binaries directly via test.sh (smoke + format conversion + tag filtering).

Upstream osmctools 0.9 audited to have NO test suite (see MANIFEST.yml
upstream_tests_exist: false + upstream_test_audit). This test_package is the
consumer-side verification.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment


class OsmctoolsTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binaries."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # Ensure the installed osmconvert/osmfilter/osmupdate binaries are on PATH
        env = Environment()
        dep = self.dependencies["osmctools"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        env.define("OSMTOOLS_BIN_DIR", bin_dir)
        env.prepend_path("PATH", bin_dir)
        env.vars(self).save_script("env_osmtools")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution (CONFIG_SHELL injected by hmbs preflight).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        dep = self.dependencies["osmctools"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        # Run test.sh smoke + functional test (source file for CI L0c compliance)
        self.run(f"{bash} test.sh \"{bin_dir}\"", env="conanrun")
