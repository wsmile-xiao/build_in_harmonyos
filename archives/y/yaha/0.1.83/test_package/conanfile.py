import os

from conan import ConanFile


class YahaTestConan(ConanFile):
    """Exercise the packaged yaha CLI on real FASTA and FASTQ reads."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'"{bash}" "{test_script}"', env="conanrun")
