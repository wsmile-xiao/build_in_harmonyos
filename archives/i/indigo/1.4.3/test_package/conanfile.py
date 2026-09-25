#!/usr/bin/env python3
"""Consumer test for the packaged Indigo core library.

Builds test_indigo.c against indigo::indigo (R34: real C API usage -
version, molecule load, canonical SMILES round-trip, reaction gross
formula, 7 assertions) and emits the HMBS machine-evidence marker.
"""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

CONSUMER_ASSERTS = 7


class IndigoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("indigo target consumers are not runnable")
        # Real test-runner call (empty-shell gate): run the consumer via
        # ctest (registered in CMakeLists.txt), then execute the binary
        # once more via subprocess to parse its deterministic assertion
        # counts. The marker is always emitted before any raise so a
        # failure keeps its evidence instead of surfacing as incomplete.
        self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanrun")
        exe = None
        for root, _, files in os.walk(self.build_folder):
            if "test_indigo" in files:
                candidate = os.path.join(root, "test_indigo")
                if os.path.isfile(candidate):
                    exe = candidate
                    break
        if exe is None:
            raise ConanException("test_indigo consumer executable is missing")
        proc = subprocess.run(
            [exe], capture_output=True, text=True, timeout=300
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        self.output.info("test_indigo output:\n" + out.strip())
        # Deterministic source: the binary's own summary line
        # "Indigo consumer checks: <passed>/<total> passed".
        discovered = 0
        passed = 0
        match = re.search(r"Indigo consumer checks: (\d+)/(\d+) passed", out)
        if match:
            passed = int(match.group(1))
            discovered = int(match.group(2))
            if discovered != CONSUMER_ASSERTS:
                self.output.error(
                    f"consumer assertion total changed: got {discovered}, "
                    f"expected {CONSUMER_ASSERTS}"
                )
                discovered = CONSUMER_ASSERTS
                passed = 0
        else:
            # Binary exited 0 but summary line missing: count as failure,
            # never fake a pass. discovered stays truthful to the audit
            # (CONSUMER_ASSERTS checks exist in test_indigo.c) while
            # passed stays 0.
            discovered = CONSUMER_ASSERTS
            self.output.error("consumer marker line missing despite exit 0")
        marker = {
            "executed": True,
            "passed": passed == discovered,
            "command": "ctest + test_indigo (indigo C API consumer)",
            "discovered": discovered,
            "passedCount": passed,
        }
        tp_marker = f"HMBS_TEST_PACKAGE_RESULT={json.dumps(marker)}"
        print(tp_marker, flush=True)
        self.output.info(tp_marker)
        if passed != discovered:
            raise ConanException(f"test_package checks failed: {marker}")
