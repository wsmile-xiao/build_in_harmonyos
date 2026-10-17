import os

from conan import ConanFile


class FastkTestConan(ConanFile):
    """test_package for FastK — runs the FastK binary and verifies output.

    R34: the test must actually execute the FastK binary (not a print-only
    stub).  We run ``FastK`` with no arguments to confirm it prints its
    usage banner (the upstream-defined behaviour for missing input), then
    we attempt a minimal k-mer counting run on a tiny synthetic FASTA and
    check that the expected histogram (``.hist``) file is produced.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries reliably;
        # use bash to wrap binary execution (same pattern as f3 test_package).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} test.sh', env="conanrun")
