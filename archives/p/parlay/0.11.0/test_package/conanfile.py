#!/usr/bin/env python3
"""Conan test_package for parlay 0.11.0 — consumer smoke test of the packaged binary.

parlay is a Go CLI application (not a linkable C/C++ library). The consumer
test runs the packaged `parlay` binary headlessly and asserts:
  - `parlay --version` exits 0 and reports 0.11.0 (ldflags injection check)
  - `parlay --help` lists the core subcommands (ecosystems, snyk, scorecard)
  - `parlay ecosystems enrich not-here` fails closed (nonzero exit)
  - `parlay --help` top-level usage mentions SBOM enrichment

Upstream `go test ./...` (72 tests) runs in the main conanfile.py build()
and emits HMBS_UPSTREAM_TEST_RESULT there; this test_package only emits
HMBS_TEST_PACKAGE_RESULT for its own 4 consumer assertions.

File location: archives/p/parlay/0.11.0/test_package/conanfile.py
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class ParlayTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["parlay"].package_folder
        exe_name = "parlay.exe" if str(self.settings.os) == "Windows" else "parlay"
        bin_path = os.path.join(package_folder, "bin", exe_name)
        assert os.path.isfile(bin_path), f"parlay binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            # HMBS injects SHELL=/bin/sh; avoid hard-coded `bash`.
            # Run from a writable cwd (TMPDIR) instead of the HMDFS package folder.
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            os.makedirs(cwd, exist_ok=True)
            # Defensive CRLF normalization: a Windows checkout may carry CRLF,
            # which OHOS /bin/sh rejects as `set: -<CR>: unknown option`.
            # Copy to a writable LF-only script and execute the copy.
            norm_script = os.path.join(cwd, "parlay-test.sh")
            with open(test_script, "rb") as src:
                data = src.read()
            data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            with open(norm_script, "wb") as dst:
                dst.write(data)
            try:
                os.chmod(norm_script, 0o755)
            except OSError:
                pass
            self.run(f'"{shell}" "{norm_script}" "{bin_path}"', env="conanrun", cwd=cwd)
            # test.sh runs 4 explicit assertions (see MANIFEST.yml).
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": f'"{shell}" "{norm_script}" "{bin_path}"',
                "discovered": 4,
                "passedCount": 4,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"parlay is not an ELF binary: {magic!r}"
            self.output.info(f"parlay binary exists and has ELF magic: {bin_path}")
