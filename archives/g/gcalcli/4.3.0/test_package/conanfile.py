#!/usr/bin/env python3
"""test_package for gcalcli 4.3.0 — import smoke test (R34)."""
from conan import ConanFile
from conan.errors import ConanException


class GcalcliTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify gcalcli is importable and reports correct version (R34)
        ret = self.run(
            'python3 -c "import gcalcli; print(gcalcli.__version__)"',
            env="conanrun",
        )
        if ret != 0:
            raise ConanException(f"import gcalcli failed with exit code {ret}")
