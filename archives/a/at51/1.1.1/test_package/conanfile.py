import os

from conan import ConanFile
from conan.tools.build import can_run


class At51TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        package = self.dependencies["at51"].package_folder
        executable = os.path.join(package, "bin", "at51")
        firmware = os.path.join(self.build_folder, "test-8051.bin")

        # A repeated LJMP instruction sequence forms a deterministic 8051-like
        # input and exercises the installed `stat` analysis subcommand.
        with open(firmware, "wb") as firmware_file:
            firmware_file.write(bytes((0x02, 0x00, 0x00)) * 1366)

        self.run(f'"{executable}" stat "{firmware}"', env="conanrun")
