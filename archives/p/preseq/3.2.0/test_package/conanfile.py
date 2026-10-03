"""Run the packaged preseq against a real upstream counts histogram."""

import os
import shlex
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class PreseqTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        program = os.path.join(package, "bin", "preseq")
        fixture = os.path.join(self.source_folder, "SRR1301329_1M_hist.txt")
        output = Path(self.build_folder, "preseq-consumer.tsv")
        if output.exists():
            raise ConanInvalidConfiguration("consumer output path is not fresh")
        command = " ".join(shlex.quote(arg) for arg in (
            program, "lc_extrap", "-H", "-o", str(output), fixture,
        ))
        self.run(command, env="conanrun")
        verifier = os.path.join(self.source_folder, "verify_output.py")
        self.run(" ".join(shlex.quote(arg) for arg in (
            "python3", verifier, str(output),
        )), env="conanrun")
        self.output.info("PRESEQ_CONSUMER_PASS: histogram extrapolation")
