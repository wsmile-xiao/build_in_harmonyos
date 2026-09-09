import os

from conan import ConanFile
from conan.tools.build import can_run


class MultiGitStatusTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = ["VirtualRunEnv"]
    test_type = "explicit"
    exports_sources = "test_mgitstatus.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("Cannot run binaries in this environment; execution validation delegated to CI conan test")
            return
        pkg = self.dependencies["multi-git-status"]
        executable = os.path.join(pkg.package_folder, "bin", "mgitstatus")
        self.run(f'bash "{os.path.join(self.source_folder, "test_mgitstatus.sh")}" "{executable}"', env="conanrun")
