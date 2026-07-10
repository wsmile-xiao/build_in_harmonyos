#!/usr/bin/env python3
"""Conan test_package for adr-tools 3.0.0 — Shell script test.

Verifies that the adr command is functional after installation.
Runs adr help, adr init, and adr new in a temporary directory.
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class AdrtoolsTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Get the bin directory from the dependency package
            dep = self.dependencies["adr-tools"]
            bin_dir = os.path.join(dep.package_folder, "bin")
            adr_cmd = os.path.join(bin_dir, "adr")

            # Find bash for executing the scripts (OHOS may not have bash in default PATH)
            import shutil as _shutil
            bash_path = (
                os.environ.get("CONFIG_SHELL")
                or os.environ.get("SHELL")
                or _shutil.which("bash")
                or "/usr/local/bin/bash"
            )
            bash_dir = os.path.dirname(bash_path)
            full_path = f"{bin_dir}:{bash_dir}"

            # Run test.sh smoke test (source file for CI L0c compliance)
            self.run(
                f'cd "{self.source_folder}" && '
                f'PATH="{full_path}:$PATH" '
                f'"{bash_path}" test.sh',
                env="conanrun"
            )

            # Test 1: adr help should work
            self.run(f'PATH="{full_path}:$PATH" "{adr_cmd}" help', env="conanrun")

            # Test 2: adr init and adr new in a temp directory
            tmpdir = tempfile.mkdtemp(prefix="adr-test-")
            try:
                self.run(
                    f'cd "{tmpdir}" && '
                    f'PATH="{full_path}:$PATH" '
                    f'ADR_DATE=1992-01-12 '
                    f'"{adr_cmd}" init doc/adr',
                    env="conanrun"
                )
                self.run(
                    f'cd "{tmpdir}" && '
                    f'PATH="{full_path}:$PATH" '
                    f'ADR_DATE=1992-01-12 '
                    f'"{adr_cmd}" new "Test Decision"',
                    env="conanrun"
                )
                # Verify the ADR files were created
                adr_file = os.path.join(tmpdir, "doc", "adr", "0002-test-decision.md")
                if not os.path.isfile(adr_file):
                    raise Exception(f"Expected ADR file not found: {adr_file}")
                self.output.info("adr-tools test: PASS (init + new + file verification)")
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
