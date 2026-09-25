#!/usr/bin/env python3
"""test_package for integrit 4.1 — a consumer-side executable smoke test.

integrit ships an executable (no linkable library is installed), so this is a
`VirtualRunEnv` test that drives the real installed binary rather than
compiling a CMake consumer against `cpp_info.libs`.

`test.sh` asserts the binary's self-reported version fingerprint plus the
full three-valued exit-code contract (0 = no change, 1 = changes, 2 = failure)
— the same contract the upstream suite exercises.
"""
from conan import ConanFile


class IntegritTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Real consumer execution (L1a/L1b/L1d): drives the `integrit` binary
        # resolved from PATH exactly as this package installs it.
        self.run("sh test.sh", env="conanrun")
