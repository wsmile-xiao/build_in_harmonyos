#!/usr/bin/env python3
"""test_package for procps 4.0.7 — validates libproc2 C API + CLI binaries.

R34: real tests, no empty shells — two layers:
  1. C API layer  — test_procps.c links against the packaged libproc2 and
     calls procps_uptime(), procps_loadavg() and the pids API
     (procps_pids_new/get/unref with PIDS_VAL(EU_PID, s_int, stack)),
     asserting uptime > 0 and that PIDs are fetched.
  2. Binary layer — runs the packaged real binaries and asserts output:
     ps --version contains "procps-ng", free contains "Mem",
     uptime contains "load average".
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class ProcpsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Compiling + linking test_procps.c against the packaged libproc2
        # already proves the library and headers are consumable.
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _run_and_capture(self, command):
        """Run a command in the conanrun environment, return its stdout."""
        out_path = os.path.join(self.build_folder, "capture.out")
        with open(out_path, "w") as f:
            self.run(command, stdout=f, env="conanrun")
        with open(out_path, "r") as f:
            return f.read()

    def test(self):
        # ── Layer 1: libproc2 C API binary (built in build()) ──
        api_test = os.path.join(
            self.cpp.build.bindirs[0], "test_procps"
        )
        if not os.path.isfile(api_test):
            raise ConanException(f"missing API test executable: {api_test}")

        if not can_run(self):
            # Cross build: compilation + linking against the packaged
            # libproc2 validates the C API (R34); runtime is validated on
            # the OHOS device/emulator.
            self.output.info(
                "cross build: test_procps linked against the packaged "
                "libproc2 — runtime validated on OHOS device"
            )
            return

        self.run(f'"{api_test}"', env="conanrun")

        # ── Layer 2: packaged CLI binary output assertions ──
        bin_dir = self.dependencies["procps"].cpp_info.bindirs[0]

        ps_bin = os.path.join(bin_dir, "ps")
        if not os.path.isfile(ps_bin):
            raise ConanException(f"missing packaged binary: {ps_bin}")
        out = self._run_and_capture(f'"{ps_bin}" --version')
        if "procps-ng" not in out:
            raise ConanException(
                f"ps --version output missing 'procps-ng': {out!r}"
            )

        free_bin = os.path.join(bin_dir, "free")
        if not os.path.isfile(free_bin):
            raise ConanException(f"missing packaged binary: {free_bin}")
        out = self._run_and_capture(f'"{free_bin}"')
        if "Mem" not in out:
            raise ConanException(f"free output missing 'Mem': {out!r}")

        uptime_bin = os.path.join(bin_dir, "uptime")
        if not os.path.isfile(uptime_bin):
            raise ConanException(f"missing packaged binary: {uptime_bin}")
        out = self._run_and_capture(f'"{uptime_bin}"')
        if "load average" not in out:
            raise ConanException(
                f"uptime output missing 'load average': {out!r}"
            )
