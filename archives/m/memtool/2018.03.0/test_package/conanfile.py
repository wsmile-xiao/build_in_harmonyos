#!/usr/bin/env python3
"""Exercise memtool against a temporary regular file."""
import os
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class MemtoolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        binary = os.path.join(
            self.dependencies["memtool"].package_folder, "bin", "memtool"
        )
        script = os.path.join(self.source_folder, "test_memtool.sh")
        with tempfile.TemporaryDirectory(
            prefix="memtool-test-",
            dir=os.environ.get("TMPDIR"),
        ) as temporary:
            data = os.path.join(temporary, "memory.bin")
            self.run(
                f'sh "{script}" "{binary}" "{data}"',
                env="conanrun",
            )
