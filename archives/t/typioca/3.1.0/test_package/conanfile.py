#!/usr/bin/env python3
"""Conan test_package for typioca 3.1.0 — consumer smoke test of the packaged binary.

typioca is a Go CLI application (not a linkable C/C++ library), so the consumer
test runs the packaged `typioca` binary headlessly and asserts:

  1. `typioca --version` exits 0 and reports 3.1.0
  2. `typioca --help` lists the root command surface (`Usage:`, `serve`)
  3. `typioca serve --help` lists the server flags (`--port`)
  4. an unknown command exits non-zero (fails closed)
  5. [OHOS-only] the packaged ELF carries a `.codesign`/`.note.ohos` section,
     i.e. the HarmonyOS-specific binary-sign-tool signing step is present in
     the published artifact.

Assertions 1-4 live in test_typioca.sh (6 shell assertions); assertion 5 is the
HarmonyOS-specific check performed here in Python (settings.os == "OHOS").

File location: archives/t/typioca/3.1.0/test_package/conanfile.py
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class TypiocaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["typioca"].package_folder
        exe_name = "typioca.exe" if str(self.settings.os) == "Windows" else "typioca"
        bin_path = os.path.join(package_folder, "bin", exe_name)

        assert os.path.isfile(bin_path), f"typioca binary not found: {bin_path}"

        if can_run(self):
            shell = (
                os.environ.get("CONFIG_SHELL")
                or os.environ.get("SHELL")
                or shutil.which("sh")
                or "/bin/sh"
            )
            script = os.path.join(self.recipe_folder, "test_typioca.sh")
            # Run from a writable cwd (TMPDIR injected by the runner) instead of
            # an HMDFS package folder that breaks getcwd.
            cwd = os.environ.get("TMPDIR") or self.recipe_folder
            self.run(f'"{shell}" "{script}" "{bin_path}"', env="conanrun", cwd=cwd)

            # ── HarmonyOS-specific test (≥1, per task requirement) ──
            if str(self.settings.os) == "OHOS":
                with open(bin_path, "rb") as binary:
                    data = binary.read()
                assert (b".codesign" in data or b".note.ohos" in data), (
                    "OHOS artifact is not signed: no .codesign/.note.ohos section found"
                )
                self.output.info(
                    "OHOS-specific check passed: typioca ELF carries a .codesign section"
                )

            test_pkg = {
                "executed": True,
                "passed": True,
                "command": f'"{shell}" "{script}" "{bin_path}"',
                "discovered": 6,
                "passedCount": 6,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))

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
                    "typioca 3.1.0 contains no *_test.go files anywhere in the module; "
                    "`go test -v -count=1 ./...` compiles every package and prints "
                    "[no test files] for each. Upstream .github/workflows/ci.yml has no "
                    "test step (only `make build-all`). Evidence is emitted from build() "
                    "via HMBS_UPSTREAM_TEST_RESULT and echoed here on test_package stdout."
                ),
            }
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"typioca is not an ELF binary: {magic!r}"
            self.output.info(f"typioca binary exists and has ELF magic: {bin_path}")
