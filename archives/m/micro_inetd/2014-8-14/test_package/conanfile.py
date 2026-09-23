#!/usr/bin/env python3
"""Conan test_package — micro_inetd 2014-8-14 CLI tool verification.

micro_inetd is an inetd-style spawner (CLI tool, not a library), so the
test binary receives the path of the INSTALLED `micro_inetd` executable
and drives it end-to-end: it forks the spawner on an ephemeral loopback
port, connects TCP clients, and verifies the socket→stdin/stdout contract
(dup2 + exec) of the service it spawns, including exit-status handling,
concurrent/repeated connections and invalid-command handling (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MicroInetdTestConan(ConanFile):
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
        inetd_bin = os.path.join(
            self.dependencies["micro_inetd"].package_folder, "bin", "micro_inetd"
        )
        test_bin = os.path.join(self.build_folder, "test_micro_inetd")
        svc_cat = os.path.join(self.build_folder, "svc_cat")
        svc_exit42 = os.path.join(self.build_folder, "svc_exit42")
        self.run(f'"{test_bin}" "{inetd_bin}" "{svc_cat}" "{svc_exit42}"', env="conanrun")
