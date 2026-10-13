#!/usr/bin/env python3
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class VtgrabTestConan(ConanFile):
    """test_package for vtgrab 0.1.8 — three console tools, no library API.

    test_package/test.sh drives the installed rvc / rvcd / twiglet executables:
    CLI contract, a real RVC 001.000 protocol handshake against a live rvcd, and
    an ELF fingerprint check that the artifacts are OHOS aarch64 musl binaries.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # vtgrab installs executables only; there is nothing to compile or link
        # against the package.
        pass

    def _shell(self):
        """Prefer an absolute bash: OHOS' default PATH carries no bash."""
        if str(self.settings.os) == "OHOS" and os.path.exists("/data/service/hnp/bin/bash"):
            return "/data/service/hnp/bin/bash"
        return os.environ.get("CONFIG_SHELL", "bash")

    def test(self):
        if not can_run(self):
            raise ConanException("vtgrab produces executables that cannot run here")
        # The protocol and ELF probes need an interpreter; reuse the one running
        # Conan instead of relying on python3 being on the conanrun PATH.
        os.environ["VTGRAB_PYTHON"] = sys.executable
        test_script = os.path.join(self.recipe_folder, "test.sh")
        self.run(f'"{self._shell()}" "{test_script}"', env="conanrun")
