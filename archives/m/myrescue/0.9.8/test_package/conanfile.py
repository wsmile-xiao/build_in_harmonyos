#!/usr/bin/env python3
"""Conan test_package for myrescue 0.9.8.

R34/R51: `test.sh` runs the three installed binaries against real files and
asserts on recovered bytes, on the block-bitmap encoding and on both bitmap
inspectors — nothing here merely prints a version string.
"""
import os
import shutil
import tempfile

from conan import ConanFile


class MyrescueTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Conan 2 exposes the resolved package folder on the dependency
        # interface itself; `cpp_info` aggregates components and has no
        # `package_folder` attribute.
        pkg_folder = self.dependencies["myrescue"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")

        # /tmp is read-only on the target (E002), so the scratch area comes
        # from Python's tempdir resolution (TMPDIR -> $HOME on this device).
        work = tempfile.mkdtemp(prefix="myrescue-test-")

        # OHOS has no /bin/bash; hnp bash is the reliable one, and plain sh
        # (hishell) is kept as a fallback because test.sh is POSIX-only.
        runner = ""
        for candidate in (os.environ.get("CONFIG_SHELL"),
                          "/data/service/hnp/bin/bash",
                          "/bin/sh"):
            if candidate and os.path.exists(candidate):
                runner = candidate
                break
        if not runner:
            runner = "sh"

        script = os.path.join(self.recipe_folder, "test.sh")
        try:
            self.run(f'{runner} "{script}" "{bin_dir}" "{work}"',
                     env="conanrun")
        except Exception:
            self.output.error(f"myrescue functional test workspace kept for "
                              f"inspection: {work}")
            raise
        shutil.rmtree(work, ignore_errors=True)
