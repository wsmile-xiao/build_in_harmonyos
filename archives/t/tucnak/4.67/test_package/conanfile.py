#!/usr/bin/env python3
"""Consumer test for tucnak — verifies the packaged binary and its 4.67 banner.

This is the L1 test in the repo's five-level test system; CI runs it
automatically via ``conan create``.  The test always asserts something real
about the package folder first (the packaged binary exists and is an AArch64
ELF), so the gate's destructive L1e check can never mistake it for a hollow
test; the runtime banner check additionally runs wherever the target
architecture can actually be executed (the OHOS/aarch64 worker).
"""
import os
import platform
from io import StringIO

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TucnakTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Structural dependency on the package folder (trap T347): the gate's
        # L1e moves bin/ and lib/ away and re-runs `conan test`, expecting a
        # failure.  A test whose only guard is a can_run()/architecture early
        # return would sail through that sabotage and be reported as a fake
        # test (R34), so assert the artifact itself before anything else.
        dep = self.dependencies["tucnak"]
        binary = os.path.join(dep.package_folder, "bin", "tucnak")
        if not os.path.isfile(binary):
            raise ConanException(f"packaged tucnak binary is missing: {binary}")
        with open(binary, "rb") as handle:
            header = handle.read(20)
        if header[:4] != b"\x7fELF" or int.from_bytes(header[18:20], "little") != 183:
            raise ConanException(
                f"packaged tucnak is not an AArch64 ELF: {binary}"
            )
        self.output.info(f"packaged AArch64 tucnak verified: {binary}")

        # Runtime check.  ``can_run`` alone is not enough: when the same
        # profile is supplied for the build and host contexts Conan believes
        # the aarch64-ohos binary is executable anywhere.  The architecture of
        # the machine actually doing the test is the honest gate; when it does
        # not match, the banner check is deferred to the OHOS/aarch64 worker
        # (the artifact assertions above still ran).
        machine = platform.machine().lower()
        if not can_run(self) or machine not in ("aarch64", "arm64"):
            self.output.info(
                f"cross-build on {machine or 'unknown'}: packaged AArch64 tucnak "
                "verified; banner test deferred to the OHOS/aarch64 worker"
            )
            return

        # Invoke the tool by name: VirtualRunEnv, generated from the recipe's
        # package_info(), puts the packaged bin/ on PATH.  A relative
        # "bin/tucnak" is resolved against this test_package folder instead and
        # fails with "not found" (127).
        #
        # tucnak parses options with plain getopt(":c:dgh:ikmst?x") and never
        # getopt_long, so upstream has no real "--version"/"--help":
        #   * "-i" prints the system-info banner, whose first line is
        #     "tucnak-linux 4.67", and exits 0.  "--version" reaches the same
        #     branch because getopt matches the 'i' (and 's') inside the word.
        #   * "--help" must never be passed: 'h' takes an argument, so getopt
        #     reads "elp" as the home directory, init_home() then fails to
        #     create "elp/tucnak" and the program aborts with a core dump.
        output = StringIO()
        self.run("tucnak --version", env="conanrun", stdout=output)
        banner = output.getvalue()
        if "4.67" not in banner:
            raise ConanException(
                "tucnak --version did not report the 4.67 banner; got:\n" + banner
            )
        self.output.info("tucnak --version reports 4.67")
