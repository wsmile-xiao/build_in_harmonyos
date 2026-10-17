#!/usr/bin/env python3
"""Conan test_package for atlantis 0.46.0

atlantis is a Go command-line application + server (Terraform Pull
Request Automation).
This test package verifies the installed `atlantis` binary is functional
by running it with the `version` subcommand (R34: substantive
dependency).

atlantis version outputs "atlantis ..." and exits 0.

R34 substantive dependency: the test executes the packaged `atlantis`
binary directly from `<package_folder>/bin/atlantis`. CI L1e sabotages
that bin/ directory; if the binary is missing the test must FAIL,
proving the test genuinely depends on the atlantis package.
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class AtlantisTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: invoke the actual installed atlantis binary (not a stub).
        pkg = self.dependencies["atlantis"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        atlantis_src = os.path.join(bin_dir, "atlantis")

        if not os.path.isfile(atlantis_src):
            raise AssertionError(
                f"R34: packaged atlantis binary not found at {atlantis_src} — "
                "test genuinely depends on the atlantis package."
            )

        # Copy into the test build folder and execute from there.
        copy(self, "atlantis", src=bin_dir, dst=self.build_folder)
        atlantis_bin = os.path.join(self.build_folder, "atlantis")

        # R34/R9: run the actual binary and verify the output.
        import io
        buf = io.StringIO()
        ret = self.run(
            f'"{atlantis_bin}" version',
            stdout=buf, stderr=buf, env="conanrun", ignore_errors=True,
        )
        out = buf.getvalue().strip()
        if ret != 0:
            raise AssertionError(f"atlantis version exited {ret}: {out}")
        if "atlantis" not in out:
            raise AssertionError(f"atlantis version output missing 'atlantis': {out}")
        if "[PLACEHOLDER]" in out:
            # R9: reject placeholder binaries unconditionally. The CI runner
            # must have Go available; if the placeholder is shipped, the
            # genuine Go build was skipped.
            raise AssertionError(
                f"R9: atlantis version produced a PLACEHOLDER binary output: {out!r} — "
                "genuine Go build required, not placeholder stub."
            )
        self.output.info(f"PASS: atlantis version output: {out}")
