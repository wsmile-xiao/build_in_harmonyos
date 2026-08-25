#!/usr/bin/env python3
"""Conan test_package for hf-mount 0.9.0 — consumer smoke test only.

Runs the packaged ``hf-mount`` management CLI via test.sh (3 consumer
cases: --version / --help / status with no daemons) and emits the
HMBS_TEST_PACKAGE_RESULT marker.

The upstream ``cargo test`` suite runs in the recipe's build() phase
against the source() downloaded-and-verified source directory, and its
HMBS_UPSTREAM_TEST_RESULT marker is emitted from build() into the conan
create log. test_package no longer re-downloads the upstream tarball
from GitHub (CI feedback round 2 — the runtime re-download hit HTTP 429
rate limiting), so there is no network dependency here and upstream vs
consumer test statistics stay independent.
"""
import os

from conan import ConanFile


class HfMountTestConan(ConanFile):
    """test_package — runs the packaged hf-mount binary via test.sh
    (consumer smoke test, HMBS_TEST_PACKAGE_RESULT marker emitted by the
    harness). Upstream cargo tests run in the recipe build() phase."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Consumer smoke test — test.sh emits HMBS_TEST_PACKAGE_RESULT
        # with real case counts. HMBS injects SHELL=/bin/sh,
        # CONFIG_SHELL=/bin/sh (platform diagnostic shell_getcwd); use the
        # injected shell to run the harness.
        bash = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "sh"
        self.run(f"{bash} test.sh", env="conanrun")
