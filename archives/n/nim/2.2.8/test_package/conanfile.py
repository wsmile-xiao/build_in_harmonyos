import os

from conan import ConanFile


class NimTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Execute the nim binary and verify output contains version info
        nim_bindir = self.dependencies["nim"].cpp_info.bindirs[0]
        nim_path = os.path.join(nim_bindir, "nim")

        # Run nim --version and verify output contains "Nim" and "2.2.8"
        self.run(f'"{nim_path}" --version 2>&1 | grep -F "Nim"')
        self.run(f'"{nim_path}" --version 2>&1 | grep -F "2.2.8"')
