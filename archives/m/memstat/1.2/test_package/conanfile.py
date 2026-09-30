#!/usr/bin/env python3
"""Consumer test for memstat 1.2.

R34: this does not print anything in place of a check.  It compiles a real C
harness (test_memstat.c) that fork/execs the packaged bin/memstat and asserts
on the binary's real exit status and real output, then runs that harness.

No CMakeToolchain is used on purpose: CMake has no HarmonyOS platform module
on this toolchain, so even a trivial project() fails compiler identification
(smemstat / dhcpoptinj precedent).  The single translation unit is compiled
directly with the compiler taken from Conan conf -- R33 forbids reading
${CC} from the shell environment.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class MemstatTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        src = os.path.join(self.source_folder, "test_memstat.c")
        out = os.path.join(self.build_folder, "test_memstat")
        self.run(f'"{cc}" -O2 -Wall "{src}" -o "{out}"')

    def test(self):
        # Assert the real artifact exists before executing anything: a package
        # that shipped no binary must fail here, not be reported as a pass.
        dep_pkg = self.dependencies[self.tested_reference_str].package_folder
        memstat_bin = os.path.join(dep_pkg, "bin", "memstat")
        if not os.path.isfile(memstat_bin):
            raise ConanException(f"packaged binary missing: {memstat_bin}")
        if not os.access(memstat_bin, os.X_OK):
            raise ConanException(f"packaged binary is not executable: {memstat_bin}")

        if not can_run(self):
            # Only reachable when the test binary itself cannot execute on the
            # build host; say so loudly instead of silently reporting success.
            print(f"[skip] {memstat_bin} cannot be executed on this host; "
                  "runtime assertions not evaluated")
            return

        # The harness is the assertion layer: it runs the packaged binary
        # through the PATH that VirtualRunEnv builds from the package's bin/
        # directory and checks the real exit status and output of each run.
        # (The binary is not invoked directly here because `memstat -v`
        # legitimately exits 1, which conan would report as a test failure.)
        test_bin = os.path.join(self.build_folder, "test_memstat")
        self.run(f'"{test_bin}"', env="conanrun")
