import os

from conan import ConanFile


class SkaTestConan(ConanFile):
    """test_package for the ska executable — runs test.sh which invokes the binary.

    test.sh exercises the OHOS consumer workflow end-to-end:
    version banner -> fasta -> split-kmer file -> info -> distance,
    including gzip-compressed input (zlib linkage feasibility).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
