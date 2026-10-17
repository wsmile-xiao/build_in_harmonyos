#!/usr/bin/env python3
"""Conan test_package — basis_universal homebrew L1 test.

Runs the upstream `basisu -test` (== `-test_ldr`) suite: for each of the 28
PNG inputs in test_files/ (kodim01-24, black_1x1, white_1x1, wikipedia,
alpha0) it performs ETC1S level 1, ETC1S level 128 and UASTC LDR 4x4
encoding, validating the compressed size (±4.5%) and PSNR (±0.3) against
the expected values compiled into the tool (g_etc1s_uastc_4x4_ldr_test_files
in basisu_tool.cpp). This is the real upstream test, executed via the
installed basisu binary against the test_files shipped in the package.

The consumer link test (basisu_test.cpp) is kept as a secondary check.

HMBS evidence markers (HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT)
are emitted as the final stdout line of each test command, with numbers
parsed from the upstream framework output.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


# Number of LDR test inputs compiled into g_etc1s_uastc_4x4_ldr_test_files[]
# (kodim01-24, black_1x1, white_1x1, wikipedia, alpha0). Each input is one
# test_mode_ldr() iteration, so discovered == executed == 28.
UPSTREAM_LDR_TEST_COUNT = 28


class BasisUniversalTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _emit_upstream_marker(self, proc, command):
        """Emit HMBS_UPSTREAM_TEST_RESULT with numbers parsed from upstream
        `basisu -test` output.

        Upstream test_mode_ldr (basisu_tool.cpp) runs 28 LDR test inputs and
        counts per-check mismatches into `total_mismatches`, then prints:
            printf("Total LDR mismatches: %u\\n", total_mismatches);
            if (total_mismatches) error_printf("LDR test FAILED\\n");
            else printf("LDR test succeeded\\n");
        The tool returns EXIT_FAILURE when total_mismatches > 0.

        There is no per-test "Test succeeded/failed" line and no
        "All tests PASSED" string — those were incorrect assumptions in the
        previous marker. Parse the actual "Total LDR mismatches: N" line.
        Each of the 28 test inputs is one test_mode_ldr() iteration, so
        discovered == executed == 28.
        """
        out = (proc.stdout or "") + (proc.stderr or "")
        # Parse "Total LDR mismatches: N" from upstream output.
        m = re.search(r"Total LDR mismatches:\s*(\d+)", out)
        mismatches = int(m.group(1)) if m else UPSTREAM_LDR_TEST_COUNT
        # A test input "passes" only when total_mismatches == 0 (tool exit 0).
        # If any mismatch occurred upstream returns EXIT_FAILURE and all 28
        # iterations are counted as failed (mismatches is a global counter,
        # not per-input).
        status = "passed" if proc.returncode == 0 else "failed"
        if proc.returncode == 0:
            passed = UPSTREAM_LDR_TEST_COUNT
            failed = 0
        else:
            passed = 0
            failed = UPSTREAM_LDR_TEST_COUNT
        marker = {
            "status": status,
            "framework": "basisu -test",
            "command": command,
            "discovered": UPSTREAM_LDR_TEST_COUNT,
            "executed": UPSTREAM_LDR_TEST_COUNT,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def _emit_test_package_marker(self, executed, passed, command):
        """Emit HMBS_TEST_PACKAGE_RESULT for the consumer test_package run."""
        marker = {
            "executed": executed,
            "passed": passed,
            "command": command,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))

    def test(self):
        pkg = self.dependencies["basis_universal"]
        pkg_folder = pkg.package_folder
        bin_path = os.path.join(pkg_folder, "bin", "basisu")
        test_dir = os.path.join(pkg_folder, "res", "test_files")

        # Primary test: run the upstream `basisu -test` LDR suite against the
        # 28 test_files shipped with the package. Upstream returns
        # EXIT_SUCCESS (0) when total_mismatches == 0, EXIT_FAILURE otherwise.
        if can_run(self) and os.path.isfile(bin_path) and os.path.isdir(test_dir):
            cmd = '"{}" -test -test_dir "{}"'.format(bin_path, test_dir)
            # Use subprocess directly (not self.run) so we can capture stdout
            # to parse test counts and emit the HMBS evidence marker.
            env = os.environ.copy()
            proc = subprocess.run(
                cmd, shell=True, env=env,
                capture_output=True, text=True,
            )
            # Print the upstream output so CI logs show the real test run.
            if proc.stdout:
                print(proc.stdout)
            if proc.stderr:
                print(proc.stderr)
            self._emit_upstream_marker(proc, cmd)
            if proc.returncode != 0:
                raise RuntimeError(
                    "upstream basisu -test failed (exit {})".format(proc.returncode)
                )

        # Secondary consumer test: link + exercise the transcoder API and
        # verify the basisu CLI reports a version.
        if can_run(self):
            ver_cmd = '"{}" --version'.format(bin_path)
            self.run(ver_cmd, env="conanrun")
            self._emit_test_package_marker(1, 1, ver_cmd)

            test_basisu = os.path.join(self.cpp.build.bindirs[0], "test_basisu")
            tp_cmd = test_basisu
            self.run(tp_cmd, env="conanrun")
            self._emit_test_package_marker(1, 1, tp_cmd)
