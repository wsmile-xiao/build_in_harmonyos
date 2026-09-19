#!/usr/bin/env python3
"""Consumer and HarmonyOS-specific tests for libdisorder."""

import json
import os
import platform
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibdisorderTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _runner_prefix(self):
        if platform.machine().lower() in ("aarch64", "arm64"):
            return []
        qemu = shutil.which("qemu-aarch64")
        root = os.environ.get("QEMU_LD_PREFIX")
        if not qemu:
            raise ConanInvalidConfiguration(
                "qemu-aarch64 is required to run OHOS consumer tests"
            )
        if not root or not os.path.isfile(
            os.path.join(root, "lib", "ld-musl-aarch64.so.1")
        ):
            raise ConanInvalidConfiguration(
                "QEMU_LD_PREFIX must contain lib/ld-musl-aarch64.so.1"
            )
        return [qemu, "-L", root]

    def _run(self, executable, arguments=None):
        command = self._runner_prefix() + [executable] + (arguments or [])
        self.run(" ".join(shlex.quote(part) for part in command), env="conanrun")

    def test(self):
        bindir = self.cpp.build.bindirs[0]
        api = os.path.join(bindir, "test_api")
        ohos = os.path.join(bindir, "test_ohos")
        self._run(api)
        self._run(ohos)

        dependency = self.dependencies["libdisorder"]
        ropy = os.path.join(dependency.package_folder, "bin", "ropy")
        fixture = os.path.join(self.build_folder, "ropy-fixture.bin")
        with open(fixture, "wb") as fixture_file:
            fixture_file.write(b"aabb")
        command = self._runner_prefix() + [ropy, fixture]
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=30, check=False
        )
        if completed.returncode != 0:
            raise ConanException(
                f"ropy failed ({completed.returncode}): {completed.stderr}"
            )
        match = re.fullmatch(
            r"tokens:\s+(\d+)\s+entropy:\s+([0-9.]+)\s+"
            r"metric:\s+([0-9.]+)\s+maxent:\s+([0-9.]+)\s+"
            r"ratio:\s+([0-9.]+)\s*",
            completed.stdout,
        )
        if not match:
            raise ConanException("unexpected ropy output: " + completed.stdout)
        tokens = int(match.group(1))
        entropy, metric, maximum, ratio = map(float, match.groups()[1:])
        expected = (tokens == 2 and abs(entropy - 1.0) < 1e-6
                    and abs(metric - 0.25) < 1e-6
                    and abs(maximum - 1.0) < 1e-6
                    and abs(ratio - 1.0) < 1e-6)
        if not expected:
            raise ConanException("ropy statistics do not match the aabb fixture")
        self.output.info("ropy integration test passed: " + completed.stdout.strip())

        result = {
            "executed": True,
            "passed": True,
            "command": "test_api && ropy fixture && test_ohos",
            "discovered": 3,
            "passedCount": 3,
        }
        marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
        self.output.info(marker)
        print(marker, flush=True)

        upstream_file = os.path.join(
            dependency.package_folder, "res", "upstream_test_result.json"
        )
        if not os.path.isfile(upstream_file):
            raise ConanException("packaged upstream test evidence is missing")
        with open(upstream_file, "r", encoding="utf-8") as evidence:
            upstream = json.load(evidence)
        upstream_marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            upstream, ensure_ascii=False
        )
        self.output.info(upstream_marker)
        print(upstream_marker, flush=True)

