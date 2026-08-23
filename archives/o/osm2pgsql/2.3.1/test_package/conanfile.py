#!/usr/bin/env python3
"""Conan test_package - osm2pgsql 2.3.1

R34: test_package must substantially exercise the tested package's functionality.
osm2pgsql is a CLI binary package, so tests run the binaries directly via test.sh
(smoke --version/--help + default.style shipping check).

Upstream osm2pgsql 2.3.1 has a real ctest suite (Catch2, NoDB subset = 32 cases)
integrated in conanfile.py build(); the HMBS_UPSTREAM_TEST_RESULT marker is emitted
there. This test_package is the consumer-side verification.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment


class Osm2pgsqlTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binaries."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # Ensure the installed osm2pgsql binary is on PATH and expose its dirs.
        env = Environment()
        dep = self.dependencies["osm2pgsql"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        share_dir = os.path.join(dep.package_folder, "share", "osm2pgsql")
        env.define("OSM2PGSQL_BIN_DIR", bin_dir)
        env.define("OSM2PGSQL_SHARE_DIR", share_dir)
        env.prepend_path("PATH", bin_dir)
        env.vars(self).save_script("env_osm2pgsql")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution (CONFIG_SHELL injected by hmbs preflight).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        dep = self.dependencies["osm2pgsql"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        share_dir = os.path.join(dep.package_folder, "share", "osm2pgsql")
        # Run test.sh smoke test (source file for CI L0c compliance).
        self.run(f"{bash} test.sh \"{bin_dir}\" \"{share_dir}\"", env="conanrun")
