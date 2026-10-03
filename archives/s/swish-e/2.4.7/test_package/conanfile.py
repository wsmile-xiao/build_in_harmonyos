import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException


class SwishETestConan(ConanFile):
    """Consumer test for the swish-e package.

    The heavy lifting lives in ``test_swishe.py`` (artifact assertions
    and the real index -> search CLI chain).  This file is the Conan
    driver entry point.
    """

    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["swish-e"]
        pkg = dep.package_folder
        if not pkg:
            raise ConanException("swish-e package folder not populated")

        harness = os.path.join(self.source_folder, "test_swishe.py")
        if not os.path.isfile(harness):
            raise ConanException(f"test driver not found: {harness}")

        cmd = [sys.executable, harness, "--package", pkg]
        self.output.info("swish-e consumer harness: " + " ".join(cmd))
        self.run(" ".join(shlex.quote(part) for part in cmd),
                 env="conanbuild")
