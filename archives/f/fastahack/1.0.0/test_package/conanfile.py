import os

from conan import ConanFile


class FastahackTestConan(ConanFile):
    """test_package for fastahack — runs the CLI binary and verifies output.

    R34: the test must actually execute the fastahack binary and observe real
    output (not a print-only stub).  We generate a FASTA index, extract a
    known subsequence via -r, and check the extracted bases against the
    expected upstream sequence.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: use bash to wrap binary execution (same pattern as fastk/f3).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} test.sh', env="conanrun")
