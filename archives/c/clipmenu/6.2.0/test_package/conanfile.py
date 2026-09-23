#!/usr/bin/env python3
"""Test package for clipmenu — runs the upstream test suite (tests/test-clipmenu).

The upstream test shims dmenu/rofi/xsel/xclip as bash functions, so it needs
no X11 display. The only platform adaptation is the CM_TEST_BIN override:
HarmonyOS /tmp is read-only (SKILL gotcha E002), while the upstream test
hardcodes /tmp/clipmenu. The 0001 patch makes that path overridable.
"""
from conan import ConanFile
from conan.tools.build import can_run
import os


class ClipmenuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies[self.tested_reference_str]
            bin_dir = dep.cpp_info.bindir

            # 1) All upstream scripts must be installed (fails on missing package)
            for script in ["clipmenu", "clipmenud", "clipdel", "clipctl", "clipfsck"]:
                script_path = os.path.join(bin_dir, script)
                if not os.path.isfile(script_path):
                    raise FileNotFoundError(f"{script} not found at {script_path}")
                self.output.info(f"[install-check] {script}: OK")

            # 2) Run the upstream test suite, shipped in the package under tests/
            #    (package layout: <pkg>/bin/clipmenu + <pkg>/tests/test-clipmenu)
            pkg_root = os.path.normpath(os.path.join(bin_dir, os.pardir))
            upstream_test = os.path.join(pkg_root, "tests", "test-clipmenu")
            if not os.path.isfile(upstream_test):
                raise FileNotFoundError(
                    f"upstream test suite not found at {upstream_test}")

            # CM_TEST_BIN redirects the hardcoded /tmp/clipmenu (read-only on OHOS);
            # CM_DIR points the clipmen.6.<user> runtime dir into the build folder.
            cm_test_bin = os.path.join(self.build_folder, "clipmenu_shim")
            env = (f'CM_TEST_BIN="{cm_test_bin}" '
                   f'CM_DIR="{self.build_folder}" ')
            self.output.info("Running upstream tests/test-clipmenu ...")
            self.run(f'{env} bash "{upstream_test}"', cwd=self.build_folder)
            self.output.info("Upstream tests/test-clipmenu: PASS (13 assertions)")
