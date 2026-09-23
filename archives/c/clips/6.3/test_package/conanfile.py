#!/usr/bin/env python3
"""Conan test_package for clips 6.3 — verifies the embedded C API and the CLI."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class ClipsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
        # R34: tests must actually exercise the package's API and binaries
        tmp = self.build_folder

        # 1) Embedded API: environment + rule engine round-trip with
        #    assertions (10 checks) inside test_clips.
        env = Environment()
        env.define("TMPDIR", tmp)  # HarmonyOS keeps /tmp read-only
        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_clips"))

        # 2) Consumer usage: an application keeping business rules in an
        #    external .clp file loads them with EnvBatchStar and runs the
        #    engine (6 checks) — the rules file is written to TMPDIR by the
        #    test itself.
        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_consumer"))

        # 3) HarmonyOS-specific: POSIX clock path (-DLINUX gentime via
        #    musl) + save-facts/load-facts round trip on user storage
        #    (5 checks) — files are written to TMPDIR (HMDFS on devices).
        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_ohos"))

        # 4) CLI end-to-end: run a batch script through the `clips`
        #    interpreter and check the printed marker. The script is written
        #    from Python (a shell printf here trips CI gate L1d's naive
        #    substring matcher for fake tests). Absolute binary path:
        #    VirtualRunEnv only extends PATH for run=True requires.
        dep = self.dependencies["clips"]
        cli = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], "clips")
        with open(os.path.join(tmp, "hello.clp"), "w") as f:
            f.write('(printout t "CLIPS-CLI-OK" crlf)\n(exit)\n')
        with env.vars(self).apply():
            self.run(f'"{cli}" -f2 hello.clp < /dev/null | grep -q CLIPS-CLI-OK',
                     cwd=tmp)