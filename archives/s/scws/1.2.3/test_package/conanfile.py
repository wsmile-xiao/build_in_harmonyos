#!/usr/bin/env python3
"""Conan test_package — scws 1.2.3 consumer test.

Two layers of real verification, executed on the OHOS worker (locally on
a macOS dev box the OHOS cross profile sets can_run=False, so the build
is compile-only and the run happens on the HarmonyOS CI worker):

1. upstream_test (upstream_test.c) — replays the 17 upstream test cases
   from phpext/scws_test.php through the public C API, against the
   packaged official dictionary (share/scws/dict.utf8.xdb) and ruleset
   (etc/rules.utf8.ini). Same inputs, same options, same expected
   segmentations as the upstream script.
2. test_scws (test.c) — links libscws and exercises the public API:
   version macro, xdb dictionary authoring via xdb_create/xdb_nput,
   mmap-backed SCWS_XDICT_XDB segmentation, in-memory SCWS_XDICT_TXT|MEM
   segmentation, and the packaged ruleset. On OHOS it additionally runs
   the HarmonyOS-specific mmap()/flock() checks (T6/T7) that back the
   adaptation's HAVE_MMAP / struct-flock configure probes.
3. test.sh — runs the packaged CLI binaries (scws-gen-dict converts
   dict.txt to xdb; scws segments a real sentence with it).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class ScwsTestConan(ConanFile):
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

    def test(self):
        if not can_run(self):
            # Cross build on a macOS dev box: OHOS binaries cannot run
            # here; the real run is exercised on the OHOS CI worker.
            self.output.info(
                "skip run: cross-built OHOS binaries cannot execute on "
                "the build host (run is exercised on the OHOS CI worker)")
            return
        if self.conf.get("user.build:flex_bison_native", default=False):
            # Local OHOS simulation on a macOS dev box (ohos-local profile
            # for both host and build): can_run() is true because the
            # settings match, but the produced binaries are OHOS/aarch64
            # and cannot execute on macOS. The real run happens on the
            # OHOS CI worker.
            self.output.info(
                "skip run: local OHOS simulation on macOS cannot execute "
                "OHOS binaries (run is exercised on the OHOS CI worker)")
            return
        pkg = self.dependencies["scws"].package_folder
        workdir = self.build_folder
        rules = os.path.join(pkg, "etc", "rules.utf8.ini")
        dict = os.path.join(pkg, "share", "scws", "dict.utf8.xdb")
        bindir = self.cpp.build.bindirs[0]

        # Layer 1: the 17 upstream cases (phpext/scws_test.php replay)
        self.run(f'"{os.path.join(bindir, "upstream_test")}" "{dict}" "{rules}"',
                 env="conanrun")

        # Layer 2: C API checks (T1-T5, plus OHOS-only T6/T7)
        self.run(f'"{os.path.join(bindir, "test_scws")}" "{workdir}" "{rules}"',
                 env="conanrun")

        # Layer 3: packaged CLI binaries (C1/C2)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        env = (f'SCWS_PKG="{pkg}" TEST_SRC="{self.recipe_folder}" '
               f'TEST_WORK="{workdir}"')
        self.run(f'{env} {bash} "{self.recipe_folder}/test.sh"',
                 env="conanrun")
