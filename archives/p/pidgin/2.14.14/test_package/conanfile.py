#!/usr/bin/env python3
"""Conan test_package for pidgin 2.14.14 — Conan L1 official test.

Uses CMakeDeps + CMakeToolchain (R33 compliant). CMakeLists.txt finds pidgin
via find_package(pidgin REQUIRED CONFIG). CI runs this automatically via
``conan create``.

The downstream consumer must be OHOS/ARM64 (cross-compile) — native host
execution is skipped via cross_building() check (R32).
"""
import os
import platform
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class PidginTestConan(ConanFile):
    # R33: CMakeDeps + CMakeToolchain only. AutotoolsDeps was previously listed
    # here (mistakenly) but it produces *.pc / conan_autotools_paths.sh, which a
    # CMake-based consumer never reads — pure noise in the test log. CMakeDeps
    # already populates INTERFACE_INCLUDE_DIRECTORIES for glib/libxml2 on
    # conan 2.x, so the CMakeLists.txt file(GLOB) fallback is the last-resort
    # safety net, not a hard dependency.
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

    def test(self):
        # Cross-Building detection:
        # 1. cross_building(self) — settings-based detection
        # 2. settings.arch != platform.machine() — actual binary cannot run natively
        #    (e.g. arch=armv8 but conan is running on x86_64)
        host_arch = str(self.settings.get_safe("arch", ""))
        native_machine = platform.machine().lower()
        # Conan arch naming: armv8 -> aarch64, x86_64 -> x86_64
        conan_to_machine = {"armv8": "aarch64", "x86_64": "x86_64", "amd64": "x86_64"}
        machine_arch = conan_to_machine.get(host_arch, host_arch)
        is_native_executable = (machine_arch == native_machine)
        if cross_building(self) or not is_native_executable:
            # L2 smoke test on cross-compiled binary is performed via
            # qemu-aarch64 outside this CI gate (see notes.md and
            # archives/p/pidgin/2.14.14/scripts/run_qemu_test.sh).
            self.output.info(f"cross-building: only verify compile+link (L2 via qemu-aarch64) "
                             f"[settings.arch={host_arch}, machine={native_machine}]")
            return
        # Use platform-native shell for native execution. Preference order:
        #   1. CONFIG_SHELL env (CI override for tests inside special sandboxes)
        #   2. shutil.which("bash") — respects PATH; standard on Linux/macOS/OHOS
        #   3. shutil.which("sh")   — POSIX fallback (busybox, alpine, etc.)
        #   4. /bin/sh — last-resort hard-coded path
        bash = os.environ.get("CONFIG_SHELL")
        if not bash:
            bash = (shutil.which("bash")
                    or shutil.which("sh")
                    or "/bin/sh")
        self.run(f"{bash} -c './test_pidgin'", env="conanrun")
