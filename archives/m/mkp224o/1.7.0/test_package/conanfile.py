#!/usr/bin/env python3
"""Conan test_package for mkp224o 1.7.0 — L1 consumer + OHOS tests.

Runs two scripts against the FINAL packaged binary:
1. test_functional.sh — end-to-end vanity address generation with a
   low-difficulty prefix, verifying file structure and address format
2. test_ohos.sh      — ELF/interp/.codesign/RPATH/OHOS run checks

Upstream official tests run inside the recipe's build() method:
`make test` builds the 4 KAT test binaries, then the recipe executes
each of the 4 binaries individually (4/4 pass).

All fail closed: any non-zero exit or timeout fails the test.
"""
import os
import shutil

from conan import ConanFile


class Mkp224oTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["mkp224o"]
        bindir = os.path.join(dep.package_folder, "bin")
        binary = os.path.join(bindir, "mkp224o")
        if not os.path.isfile(binary):
            raise FileNotFoundError(f"packaged mkp224o not found: {binary}")

        # bash: prefer CONFIG_SHELL/profile path, then PATH lookup.
        # Scripts are invoked via `bash script` (their shebang is not
        # used here), so only a locatable bash is required — no
        # hardcoded interpreter path; fail closed if bash is not found.
        bash = os.environ.get("CONFIG_SHELL", "")
        if not (bash and os.path.isfile(bash)):
            bash = shutil.which("bash")
        if not bash:
            raise FileNotFoundError(
                "bash not found for test scripts "
                "(set CONFIG_SHELL or put bash on PATH)"
            )

        # 1) functional test of the FINAL packaged binary
        self.run(
            f'"{bash}" test_functional.sh "{binary}"',
            env="conanrun",
            cwd=self.source_folder,
        )
        # 2) OHOS-specific checks of the final binary
        self.run(
            f'"{bash}" test_ohos.sh "{binary}"',
            env="conanrun",
            cwd=self.source_folder,
        )
        self.output.info("mkp224o: all test_package tests OK")
