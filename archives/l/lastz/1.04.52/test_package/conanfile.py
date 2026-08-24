import os

from conan import ConanFile
from conan.tools.build import can_run


class LastzTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_lastz.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        source = os.path.join(
            self.source_folder,
            "test_lastz.c",
        )

        executable = os.path.join(
            self.build_folder,
            "test_lastz",
        )

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
        )

        cc = compiler_executables.get(
            "c",
            "cc",
        )

        self.run(
            '"{}" -Wno-unused-command-line-argument "{}" -o "{}"'.format(
                cc,
                source,
                executable,
            )
        )

    def test(self):
        if not can_run(self):
            return

        dependency = self.dependencies["lastz"]

        lastz = os.path.join(
            dependency.package_folder,
            "bin",
            "lastz",
        )

        test_executable = os.path.join(
            self.build_folder,
            "test_lastz",
        )

        if not os.path.isfile(lastz):
            raise RuntimeError("packaged lastz executable not found")

        self.run(
            '"{}" "{}" "{}"'.format(
                test_executable,
                lastz,
                self.build_folder,
            )
        )
