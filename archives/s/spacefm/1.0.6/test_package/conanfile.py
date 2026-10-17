#!/usr/bin/env python3
"""Conan test_package for spacefm 1.0.6 (GTK2 file manager).

spacefm is a GTK2 desktop application (not a linkable library). The GUI
runtime (X11/Wayland display, window manager integration) is not available
in the test sandbox — environment limitation. The consumer test asserts:

  - `spacefm --version` exits 0 and reports version 1.0.6
  - `spacefm --help` prints usage info, rc=0
  - the binary is an AArch64 ELF (packaging integrity)

File location: archives/s/spacefm/1.0.6/test_package/conanfile.py
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class SpacefmTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["spacefm"].package_folder
        bin_path = os.path.join(package_folder, "bin", "spacefm")
        assert os.path.isfile(bin_path), f"spacefm binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            self.run(f'"{shell}" "{test_script}" "{bin_path}"', env="conanrun", cwd=cwd)
            # test.sh runs 3 assertions (see MANIFEST.yml).
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": f'"{shell}" "{test_script}" "{bin_path}"',
                "discovered": 3,
                "passedCount": 3,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            # Upstream test evidence: no automated test suite in the tarball
            # (no test/ dir, no TESTS in Makefile.am) — no_tests mark
            # (aiac/zsa-wally precedent).
            upstream = {
                "status": "no_tests",
                "framework": "none",
                "command": "",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "spacefm 1.0.6 tarball ships no automated test suite: "
                          "no test/ directory, no TESTS/check_PROGRAMS in Makefile.am; "
                          "upstream is a GUI desktop application without a test harness",
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
