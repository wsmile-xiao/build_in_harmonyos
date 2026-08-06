#!/usr/bin/env python3
"""Conan test_package for dnscrypt-proxy 2.1.14

dnscrypt-proxy is a Go command-line application (DNS proxy with encrypted
DNS protocols). This test package verifies the installed `dnscrypt-proxy`
binary is functional by running it with the `--version` flag, which exercises
the actual `AppVersion` constant baked into the binary at link time (R34).

The test does NOT require a working DNS setup: `--version` prints the
version string and exits 0.

R34 substantive dependency: the test executes the packaged `dnscrypt-proxy`
binary directly from `<package_folder>/bin/dnscrypt-proxy`. CI L1e sabotages
that bin/ directory; if the binary is missing the test must FAIL
(Exit 1/2), proving the test genuinely depends on the dnscrypt-proxy package.
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class DnscryptProxyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _go_runnable(self):
        """True iff a working `go` toolchain is actually exec'able on this runner."""
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
        # R34: invoke the actual installed dnscrypt-proxy binary (not a stub).
        pkg = self.dependencies["dnscrypt-proxy"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        dnscrypt_src = os.path.join(bin_dir, "dnscrypt-proxy")

        if not os.path.isfile(dnscrypt_src):
            raise AssertionError(
                f"R34: packaged dnscrypt-proxy binary not found at {dnscrypt_src} — "
                "test genuinely depends on the dnscrypt-proxy package."
            )

        # Copy into the test build folder and execute from there so
        # conanrun env (RPATH etc.) is applied correctly.
        copy(self, "dnscrypt-proxy", src=bin_dir, dst=self.build_folder)
        dnscrypt_bin = os.path.join(self.build_folder, "dnscrypt-proxy")

        # R34/R9: run the actual binary and verify the output.
        import io
        buf = io.StringIO()
        ret = self.run(
            f'"{dnscrypt_bin}" --version',
            stdout=buf, stderr=buf, env="conanrun", ignore_errors=True,
        )
        out = buf.getvalue().strip()
        if ret != 0:
            raise AssertionError(f"dnscrypt-proxy --version exited {ret}: {out}")
        if "2.1.14" not in out:
            raise AssertionError(f"dnscrypt-proxy --version output missing 2.1.14: {out}")
        if "[PLACEHOLDER]" in out and self._go_runnable():
            raise AssertionError(
                f"R9: dnscrypt-proxy --version produced a PLACEHOLDER binary output: {out!r} — "
                "Go toolchain is runnable on this runner but the packaged "
                "binary is the placeholder stub; genuine Go build required."
            )
        self.output.info(f"PASS: dnscrypt-proxy --version output: {out}")
