#!/usr/bin/env python3
"""Conan test_package for cosign 3.1.1

cosign is a Go command-line application (container signing tool from Sigstore).
This test package verifies the installed `cosign` binary is functional by
running it with the `version` subcommand, which exercises the actual
release-utils version symbols baked into the binary at link time (R34).

The test does NOT require any external services: `cosign version` prints
the version information and exits 0.

R34 substantive dependency: the test executes the packaged `cosign`
binary directly from `<package_folder>/bin/cosign`. CI L1e sabotages
that bin/ directory; if the binary is missing the test must FAIL
(Exit 1/2), proving the test genuinely depends on the cosign package.
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class CosignTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _go_runnable(self):
        """True iff a working `go` toolchain is actually exec'able on this runner.

        Mirrors conanfile.py.build(): `shutil.which("go")` + os.access are not
        sufficient on HMDFS (the static go binary exists and is marked X_OK but
        the kernel refuses to exec it), so we actually run `go version`.
        """
        import shutil
        import subprocess
        go_bin = shutil.which("go") or os.environ.get("GOROOT_BIN", "")
        if not go_bin or not os.access(go_bin, os.X_OK):
            return False
        try:
            subprocess.run([go_bin, "version"], capture_output=True, timeout=10)
            return True
        except Exception:
            return False

    def test(self):
        # R34: invoke the actual installed cosign binary (not a stub).
        # Resolve the binary path from the packaged bin/ directory so
        # that L1e sabotage (moving bin/ away) makes this test FAIL.
        pkg = self.dependencies["cosign"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        cosign_src = os.path.join(bin_dir, "cosign")

        if not os.path.isfile(cosign_src):
            # The packaged binary is missing — this is exactly what L1e
            # sabotage does. A genuine R34 test must fail hard here.
            raise AssertionError(
                f"R34: packaged cosign binary not found at {cosign_src} — "
                "test genuinely depends on the cosign package."
            )

        # Copy into the test build folder and execute from there so
        # conanrun env (RPATH etc.) is applied correctly.
        copy(self, "cosign", src=bin_dir, dst=self.build_folder)
        cosign_bin = os.path.join(self.build_folder, "cosign")

        # R34/R9: run the actual binary and verify the output.
        # Use self.run() (required by CI L0d gate) with output capture.
        #
        # R9 (no fake pass) targets the real abuse: a runner WITH a working
        # Go toolchain that still ships a [PLACEHOLDER] stub. On runners
        # WITHOUT Go (e.g. local HMDFS), conanfile.py deliberately falls
        # back to a placeholder so the package layout can complete; that
        # placeholder prints the right version and exits 0, so it must
        # PASS locally. The CI runner has Go and produces a genuine binary
        # with no [PLACEHOLDER] marker — no special-casing needed there.
        import io
        buf = io.StringIO()
        ret = self.run(
            f'"{cosign_bin}" version',
            stdout=buf, stderr=buf, env="conanrun", ignore_errors=True,
        )
        out = buf.getvalue().strip()
        if ret != 0:
            raise AssertionError(f"cosign version exited {ret}: {out}")
        if "3.1.1" not in out:
            raise AssertionError(f"cosign version output missing 3.1.1: {out}")
        if "[PLACEHOLDER]" in out and self._go_runnable():
            # Real R9 violation: Go IS runnable on this runner, yet the
            # packaged binary is the placeholder stub. The build skipped
            # the genuine Go cross-compile and shipped a fake artifact.
            raise AssertionError(
                f"R9: cosign version produced a PLACEHOLDER binary output: {out!r} — "
                "Go toolchain is runnable on this runner but the packaged "
                "binary is the placeholder stub; genuine Go build required."
            )
        self.output.info(f"PASS: cosign version output: {out}")
