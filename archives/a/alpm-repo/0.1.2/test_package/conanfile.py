import os

from conan import ConanFile
from conan.tools.build import can_run

from test_cli import HELP_ARGS, assert_executable_magic, binary_names


class AlpmRepoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["alpm-repo"].package_folder
        binaries = [
            os.path.join(package_folder, "bin", binary)
            for binary in binary_names(str(self.settings.os))
        ]

        for binary in binaries:
            if not os.path.isfile(binary):
                raise RuntimeError(f"binary not found: {binary}")

        if can_run(self):
            for binary in binaries:
                for args in HELP_ARGS:
                    self.run(f'"{binary}" {args}', env="conanrun")
        else:
            for binary in binaries:
                assert_executable_magic(binary, str(self.settings.os))
