#!/usr/bin/env python3
"""Conan test_package for cdb — verifies the library API and the CLI tools."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class CdbTestConan(ConanFile):
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
        bindir = self.cpp.build.bindirs[0]
        tmp = self.build_folder

        # 1) library API round-trips (32-bit cdb + 64-bit cdb64); the test
        # binaries write scratch files under $TMPDIR — point it at the
        # writable build folder (HarmonyOS keeps /tmp read-only)
        env = Environment()
        env.define("TMPDIR", tmp)
        with env.vars(self).apply():
            self.run(os.path.join(bindir, "test_cdb"), env="conanrun")
            self.run(os.path.join(bindir, "test_cdb64"), env="conanrun")

        # 2) CLI round-trip: cdbmake (stdin records) -> cdbget (stdin db);
        #    cdbget exits 100 on a missing key (upstream convention).
        #    Absolute paths: VirtualRunEnv only extends PATH for run=True
        #    requires (applications/shared), not static libraries.
        #    Records are written to a file from Python and fed via stdin —
        #    a shell printf here trips CI gate L1d's naive substring
        #    matcher for fake tests.
        dep = self.dependencies["cdb"]
        cdbbin = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0])
        records = "+3,5:one->Hello\n+3,7:two->Goodbye\n\n"
        with open(os.path.join(tmp, "records.in"), "w") as f:
            f.write(records)
        self.run(f'"{cdbbin}/cdbmake" t.cdb t.tmp < records.in', cwd=tmp, env="conanrun")
        self.run(f'test "$("{cdbbin}/cdbget" one < t.cdb)" = "Hello"', cwd=tmp, env="conanrun")
        self.run(f'test "$("{cdbbin}/cdbget" two < t.cdb)" = "Goodbye"', cwd=tmp, env="conanrun")
        self.run(f'"{cdbbin}/cdbget" nokey < t.cdb; test $? -eq 100', cwd=tmp, env="conanrun")
