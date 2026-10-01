#!/usr/bin/env python3
"""Conan test_package for lcdproc 0.5.9.

lcdproc 0.5.9 installs no linkable library (shared/Makefile.am declares
libLCDstuff.a as `noinst_LIBRARIES`), so the consumer-visible surface is the
executable suite.  The tests therefore execute the packaged binaries and assert
on real output (R34): the three clients' usage screens, their verbatim
connection-refused diagnostics, and the AArch64 ABI of every shipped artifact
including the LCDd driver plugins.

test.sh is invoked with the three directories resolved from the *installed*
package, so the assertions cannot accidentally pass against the build tree.
"""
import os

from conan import ConanFile


class LcdprocTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # NOTE: deliberately no `if not can_run(self): return` guard here.
        # That guard made the whole test a silent no-op whenever the packaged
        # artifacts were absent, which is precisely the fake-test shape R34
        # (and CI's L1e destructive negative test) exists to catch: L1e moves
        # bin/ and lib/ out of the package folder, re-runs the test, and a
        # guarded test() still exits 0 -> "fake test detected".  The test here
        # executes the packaged aarch64 binaries, so if they are missing it
        # must fail, not skip.
        dep = self.dependencies["lcdproc"]
        # Everything lands in bin/ (see the bindirs note in the recipe's
        # package_info): the clients plus the LCDd daemon, which upstream
        # declares as sbin_PROGRAMS.  The driver plugins go to lib/lcdproc/.
        bindir = os.path.join(dep.package_folder, "bin")
        drvdir = os.path.join(dep.package_folder, "lib", "lcdproc")
        script = os.path.join(self.source_folder, "test.sh")
        # Case 6 needs a peer on the other end of the LCDd socket; see
        # lcdd_stub.py for why the real daemon cannot play that role.
        stub = os.path.join(self.source_folder, "lcdd_stub.py")
        self.run(f'sh "{script}" "{bindir}" "{drvdir}" "{stub}"', env="conanrun")
