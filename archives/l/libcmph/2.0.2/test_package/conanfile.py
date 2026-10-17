import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # E074: HMDFS SELinux forbids the make jobserver FIFO; force -j1
        # so CMake's `make` invocation doesn't try to create one.
        cmake.build(cli_args=["-j1"])

    def test(self):
        if can_run(self):
            # R34: the test must actually exercise the packaged library.
            # perfect_hash_contract links libcmph, builds a minimal perfect
            # hash over a fixed key set, and verifies perfect/minimal/stable/
            # packed/round-trip properties.
            # No cmake_layout() (it breaks CMake on HarmonyOS); use
            # self.build_folder directly — CMake puts the binary there.
            bin_path = os.path.join(self.build_folder, "perfect_hash_contract")
            self.run(f'"{bin_path}"', env="conanrun")
