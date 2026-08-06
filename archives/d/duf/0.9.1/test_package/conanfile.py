#!/usr/bin/env python3
"""Conan test_package for duf 0.9.1

duf is a Go command-line application (Disk Usage/Free utility).
This test package verifies the installed `duf` binary is functional by
running it with the `--version` flag (R34: substantive dependency).

duf --version outputs "duf (built from source)" and exits 0.

R34 substantive dependency: the test executes the packaged `duf`
binary directly from `<package_folder>/bin/duf`. CI L1e sabotages
that bin/ directory; if the binary is missing the test must FAIL,
proving the test genuinely depends on the duf package.
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class DufTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _go_runnable(self):
        """True iff a working `go` toolchain is actually exec'able."""
        import shutil
        import subprocess
        go_bin = shutil.which("go")
        if not go_bin:
            goroot = os.environ.get("GOROOT", os.path.join(os.path.expanduser("~"), "usr", "local", "go"))
            go_bin = os.path.join(goroot, "bin", "go")
        if not go_bin or not os.access(go_bin, os.X_OK):
            return False
        try:
            subprocess.run([go_bin, "version"], capture_output=True, timeout=10)
            return True
        except Exception:
            return False

    def test(self):
        # R34: invoke the actual installed duf binary (not a stub).
        pkg = self.dependencies["duf"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        duf_src = os.path.join(bin_dir, "duf")

        if not os.path.isfile(duf_src):
            raise AssertionError(
                f"R34: packaged duf binary not found at {duf_src} — "
                "test genuinely depends on the duf package."
            )

        # Copy into the test build folder and execute from there.
        copy(self, "duf", src=bin_dir, dst=self.build_folder)
        duf_bin = os.path.join(self.build_folder, "duf")

        # R34/R9: run the actual binary and verify the output.
        import io
        buf = io.StringIO()
        ret = self.run(
            f'"{duf_bin}" --version',
            stdout=buf, stderr=buf, env="conanrun", ignore_errors=True,
        )
        out = buf.getvalue().strip()
        if ret != 0:
            raise AssertionError(f"duf --version exited {ret}: {out}")
        if "duf" not in out:
            raise AssertionError(f"duf --version output missing 'duf': {out}")
        if "[PLACEHOLDER]" in out:
            # R9: reject placeholder binaries unconditionally. The CI runner
            # must have Go available; if the placeholder is shipped, the
            # genuine Go build was skipped.
            raise AssertionError(
                f"R9: duf --version produced a PLACEHOLDER binary output: {out!r} — "
                "genuine Go build required, not placeholder stub."
            )
        self.output.info(f"PASS: duf --version output: {out}")
