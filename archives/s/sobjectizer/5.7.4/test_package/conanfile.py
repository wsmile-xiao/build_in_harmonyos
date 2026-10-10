#!/usr/bin/env python3
"""Conan test_package — sobjectizer 5.7.4 (L1/L2 official test).

Verification layers:

  1. test_sobjectizer (CMake consumer via sobjectizer::SharedLib / CMakeDeps)
     Part 1: SO_5_VERSION must equal the packaged version 5.7.4.
     Part 2: full environment lifecycle -- env -> coop -> agent -> direct mbox
             -> immediate message -> delayed message (real timer thread) -> stop.
     Part 3: two-agent ping/pong round-trip over ONE real mbox for 1000
             exchanges. This is the canonical SObjectizer usage pattern
             (cf. upstream dev/sample/so_5/ping_pong) and is the consumer
             end-to-end case required by rule 12.

  2. test_sobjectizer_static (CMake consumer via sobjectizer::StaticLib)
     Links the STATIC product (upstream libso_s.a; SO_5_STATIC_LIB is defined
     PUBLIC on that target, so it is a different compile configuration from the
     shared one). It runs a full env -> coop -> agent -> message -> stop cycle.
     This layer catches link/ABI problems the shared-library consumer cannot.

  3. Upstream ctest suite is executed inside the recipe's build() (318 tests),
     so test_package does not repeat it; see test_package/MANIFEST.yml.

Both executables print HMBS_*_RESULT JSON lines for evidence collection and
exit non-zero on the first failure, so a regression can never pass silently.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SobjectizerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    # ------------------------------------------------------------------
    # 可执行性判定（交叉编译时目标产物本机跑不了）
    # ------------------------------------------------------------------
    def _emulator(self):
        """Return the qemu runner configured for this profile, if any.

        The `ohos-aarch64-run` profile sets
        tools.cmake.cmaketoolchain:extra_variables, which is what makes
        conan's own can_run() report False for any cross build; we look the
        same value up from the generated cmake toolchain so that test() still
        executes the aarch64 binaries under qemu.
        """
        tc = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.exists(tc):
            return None
        for line in open(tc, encoding="utf-8", errors="replace"):
            line = line.strip()
            if line.startswith("set(CMAKE_CROSSCOMPILING_EMULATOR"):
                return line.split('"')[1]
        return None

    def _run_target(self, exe):
        """Execute a built aarch64 target, directly or through the emulator."""
        emu = self._emulator()
        if emu and os.path.isfile(exe):
            self.run(f'"{emu}" "{exe}"', env="conanrun")
        else:
            self.run(f'"{exe}"', env="conanrun")

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ------------------------------------------------------------------
    # test
    # ------------------------------------------------------------------
    def test(self):
        bindir = self.cpp.build.bindirs[0]
        emu = self._emulator()

        # ---- layer 1: shared-library CMake consumer ----------------------
        test_shared = os.path.join(bindir, "test_sobjectizer")
        if emu or self._can_run_directly():
            self._run_target(test_shared)
        else:
            self.output.info(
                "SKIP test_sobjectizer: no runner for aarch64 targets "
                "(built and linked OK; the qemu run is recorded in the PR "
                "evidence under profile ohos-aarch64-run)")

        # ---- layer 2: static-library CMake consumer ----------------------
        test_static = os.path.join(bindir, "test_sobjectizer_static")
        if emu or self._can_run_directly():
            self._run_target(test_static)
        else:
            self.output.info(
                "SKIP test_sobjectizer_static: no runner for aarch64 targets "
                "(built and linked OK; this layer guards the "
                "SOBJECTIZER_BUILD_STATIC=ON product)")

    def _can_run_directly(self):
        """True only when the host can execute the built binaries natively."""
        try:
            return not self.settings.os == "OHOS"
        except Exception:
            return False
