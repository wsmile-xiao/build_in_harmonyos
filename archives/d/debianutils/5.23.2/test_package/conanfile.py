import os

from conan import ConanFile


class DebianutilsTestConan(ConanFile):
    """test_package for debianutils executable — runs test.sh which invokes run-parts."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # VirtualRunEnv on OHOS may not set PATH correctly for bindirs.
        # Explicitly add the package's bin directory to PATH.
        dep = self.dependencies["debianutils"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'export PATH="{bin_dir}:$PATH" && {bash} test.sh')
