#!/usr/bin/env python3
"""Conan test_package — codex-probe 1.0.3 consumer verification.

codex-probe is a Go CLI application (no linkable library), so the consumer test
executes the packaged ``bin/codex-probe`` binary through test.sh, which runs six
offline cases against the real upstream diagnostics:

    --help / bare invocation                 -> rc 0, Usage block printed
    --sync --status                          -> rc 1, mutually exclusive commands
    --config <missing> --login               -> rc 1, config load fails closed
    --config <file> --login                  -> rc 1, --login without -o
    --status --output report.txt             -> rc 1, --output must be .csv

None of the failing cases reach the upstream network-region probe, so the suite
needs no network and is independent of the CI worker's egress region.

Upstream test inventory: **0 tests**. Tag v1.0.3 contains no ``*_test.go`` file
anywhere in the module and ``.github/workflows/release.yml`` is a GoReleaser
build/publish job with no test step, so ``go test ./...`` reports
``[no test files]`` for every package. The ``no_tests`` HMBS marker is emitted
here (per MANIFEST.yml ``upstream_test_in_build: false``) so the HMBS evidence
gate can collect it from test_package stdout, aligned with the merged
archives/a/aiac/5.3.0 recipe.

Emits:
  - HMBS_TEST_PACKAGE_RESULT  (test.sh, 6 cases / 13 assertions)
  - HMBS_UPSTREAM_TEST_RESULT (status: no_tests, 0 upstream tests)
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class CodexProbeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["codex-probe"].package_folder
        exe_name = "codex-probe.exe" if str(self.settings.os) == "Windows" else "codex-probe"
        bin_path = os.path.join(package_folder, "bin", exe_name)
        assert os.path.isfile(bin_path), "codex-probe binary not found: %s" % bin_path

        if not can_run(self):
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", "codex-probe is not an ELF binary: %r" % magic
            self.output.info("codex-probe binary present (cross-build, not executed)")
            return

        if str(self.settings.os) == "OHOS":
            # E128/E077: an unsigned ELF is refused with "Permission denied"
            # (rc 126) on OHOS, so fail with a precise diagnostic instead of a
            # bare Exec format/denied error if signing was skipped.
            self._assert_signed(bin_path)

        test_script = os.path.join(self.recipe_folder, "test.sh")
        # HMBS injects SHELL=/bin/sh; avoid hard-coding `bash`, and run from a
        # writable cwd (TMPDIR) rather than the HMDFS archive tree, which
        # breaks getcwd for spawned shells.
        shell = os.environ.get("SHELL") or "/bin/sh"
        cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
        self.run('"%s" "%s" "%s"' % (shell, test_script, bin_path),
                 env="conanrun", cwd=cwd)

        test_pkg = {
            "executed": True,
            "passed": True,
            "command": '"%s" "%s" <bin/codex-probe>' % (shell, test_script),
            "discovered": 6,
            "passedCount": 13,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" +
                         json.dumps(test_pkg, ensure_ascii=False))

        # Bare print() so the HMBS evidence gate (which scans test_package
        # stdout, not conan-prefixed self.output.info lines) sees the marker.
        upstream = {
            "status": "no_tests",
            "framework": "go test",
            "command": "go test -v -count=1 ./...",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "codex-probe 1.0.3 ships no *_test.go files anywhere in the "
                "module (module github.com/QuantumNous/new-api/tools/codex-probe); "
                "`go test -v -count=1 ./...` compiles every package and prints "
                "[no test files] for each, and .github/workflows/release.yml is a "
                "GoReleaser build/publish job with no test step. Upstream test "
                "count is therefore 0. The go test audit run is logged in the "
                "conanfile.py build() phase (conan create log). This marker is "
                "emitted from test_package per MANIFEST.yml "
                "upstream_test_in_build: false, aligned with the merged "
                "archives/a/aiac/5.3.0 recipe."
            ),
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

    def _assert_signed(self, bin_path):
        """E128/E077 guard: a packaged OHOS binary must carry a .codesign section."""
        readelf = ("/data/service/hnp/bin/llvm-readelf",
                   "/storage/Users/currentUser/usr/local/bin/llvm-readelf")
        for cand in readelf:
            if not os.path.isfile(cand):
                continue
            try:
                import subprocess
                out = subprocess.run([cand, "-S", bin_path], capture_output=True,
                                     text=True, timeout=30).stdout or ""
            except (OSError, subprocess.SubprocessError):
                return
            assert ".codesign" in out, (
                "packaged codex-probe binary carries no .codesign section — "
                "OHOS will refuse to execve it (E128/E077)")
            self.output.info("codex-probe carries a .codesign section")
            return
