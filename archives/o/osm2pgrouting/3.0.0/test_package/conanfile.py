#!/usr/bin/env python3
"""Conan test_package — osm2pgrouting 3.0.0 (CLI tool).

test.sh really executes the installed osm2pgrouting binary: it checks the
version/help output, the required-option and unrecognised-option paths, drives
a genuine libpqxx/libpq connection attempt against a port nobody listens on,
and verifies the installed routing configuration files. Nothing here is a
print-only stub (R34).
"""
import os

from conan import ConanFile


class Osm2pgroutingTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries reliably, so
        # wrap the test driver in bash (the profile provides CONFIG_SHELL).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        # The second argument is the staging root. OHOS refuses to exec an
        # unsigned ELF (EPERM, which the shell reports as exit code 126), and
        # the installed binary is unsigned -- so test.sh copies it out of the
        # package and signs the copy with /data/service/hnp/bin/binary-sign-tool
        # before running it. Staging (rather than signing in place) keeps the
        # already-computed package manifest untouched.
        self.run(
            f'{bash} test.sh "{pkg_folder}" "{self.build_folder}"', env="conanrun"
        )
