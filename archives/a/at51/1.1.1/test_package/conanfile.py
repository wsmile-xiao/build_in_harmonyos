import os

from conan import ConanFile
from conan.tools.build import can_run

from test_cli import HELP_COMMANDS, assert_executable_magic


class At51TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["at51"].package_folder
        binary = "at51.exe" if str(self.settings.os) == "Windows" else "at51"
        at51 = os.path.join(package_folder, "bin", binary)

        if not os.path.isfile(at51):
            raise RuntimeError(f"at51 binary not found: {at51}")

        if can_run(self):
            for args in HELP_COMMANDS:
                self.run(f'"{at51}" {args}', env="conanrun")
        else:
            assert_executable_magic(at51, str(self.settings.os))
