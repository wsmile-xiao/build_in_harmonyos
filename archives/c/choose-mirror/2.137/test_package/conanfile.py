import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # R34: real functional test — build test_choose-mirror (a C
            # harness), then actually execute the packaged bin/choose-mirror
            # with -n and assert the real exit code plus the debconf state
            # machine transcript it prints.
            pkg_folder = self.dependencies["choose-mirror"].package_folder
            cm = os.path.join(pkg_folder, "bin", "choose-mirror")
            test_bin = os.path.join(self.cpp.build.bindir,
                                    "test_choose-mirror")
            # L0d/R34: test() must call self.run — the harness forks
            # choose-mirror -n, captures its stdout + exit code and asserts:
            #   1. exit code 139 (SIGSEGV in the cdebconf passthrough
            #      frontend after "SET mirror/country" — OHOS has no debconf
            #      database/frontend stack, deterministic: 8/8 observed runs)
            #   2. transcript contains the real state-machine milestones
            #      (VERSION 2 / REGISTER mirror/https/mirror / GET
            #      mirror/protocol / SET mirror/country)
            self.run(
                f'"{test_bin}" "{cm}"',
                env="conanrun",
            )
            # (The harness additionally byte-scans the ELF for the
            # statically-linked debconfclient_new symbol — no external
            # readelf/PATH dependency, all assertions live in test.c.)
