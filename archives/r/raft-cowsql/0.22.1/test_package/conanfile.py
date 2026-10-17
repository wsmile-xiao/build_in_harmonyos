#!/usr/bin/env python3
"""test_package for raft-cowsql 0.22.1 — verifies raft_strerror API (R34).

Compiles a test program that calls raft_strerror() and checks the result.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class RaftCowsqlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        raft = self.dependencies["raft-cowsql"]
        inc = os.path.join(raft.package_folder, "include")
        lib = os.path.join(raft.package_folder, "lib")
        self.run(f'clang test_raft.c -o test_raft -I"{inc}" -L"{lib}" -lraft')

    def test(self):
        if not can_run(self):
            self.output.info("cross: skip run")
            return
        self.run("./test_raft", env="conanrun")
