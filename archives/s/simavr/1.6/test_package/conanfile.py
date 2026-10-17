from conan import ConanFile
from conan.tools.build import can_run
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libsimavr.a's sim_elf.o references libelf symbols — the consumer
        # link needs -lelf, so require libelf in the test graph
        self.requires("libelf/0.8.13")

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["simavr"].package_folder
        elf = self.dependencies["libelf"].package_folder
        # link a consumer against libsimavr (real API check, R34)
        test_script = os.path.join(os.path.dirname(__file__), "test_simavr.py")
        self.run(f"python3 '{test_script}' '{pkg}' "
                 f"'{os.path.join(elf, 'lib')}'",
                 env="conanrun")
