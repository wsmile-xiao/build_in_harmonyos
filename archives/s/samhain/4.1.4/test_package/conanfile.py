import os

from conan import ConanFile
from conan.tools.build import can_run


class SamhainTestConan(ConanFile):
    """test_package for samhain — local file: integrity chain, no daemon/network.

    Runs test_samhain.sh through VirtualRunEnv (samhain's bin/ lands on PATH).
    The five assertions exercise shipped code paths without any config file,
    daemon or socket:
      1. samhain -v reports the packaged version 4.1.4
      2. samhain -H is deterministic and matches the published TIGER vector
      3. samhain --create-database builds a checksum database from a file list
      4. samhain --verify-database passes on the untampered tree
      5. samhain --verify-database detects a tampered file (non-zero exit)
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("can_run() is false, skipping consumer test on cross build")
            return
        script = os.path.join(os.path.dirname(__file__), "test_samhain.sh")
        self.run(f'sh "{script}"', env="conanrun")
