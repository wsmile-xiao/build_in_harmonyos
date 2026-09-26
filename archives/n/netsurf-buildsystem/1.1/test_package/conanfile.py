import os

from conan import ConanFile


class NetsurfBuildsystemTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        dependency = self.dependencies.build["netsurf-buildsystem"]
        shared = os.path.join(
            dependency.package_folder, "share", "netsurf-buildsystem"
        )
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{test_script}" "{shared}"', env="conanbuild")
