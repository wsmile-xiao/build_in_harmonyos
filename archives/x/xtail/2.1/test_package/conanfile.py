"""Consumer smoke test for the installed xtail executable."""
import os
import platform

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class XtailTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        executable = os.path.join(package, "bin", "xtail")
        # Verify the installed artifact even when target execution is
        # unavailable. L1e removes bin/ and must cause this test to fail.
        if not os.path.isfile(executable):
            raise ConanException("xtail package executable missing")
        with open(executable, "rb") as handle:
            elf = handle.read(20)
        if elf[:4] != b"\x7fELF" or elf[18:20] != b"\xb7\x00":
            raise ConanException("xtail package is not an AArch64 ELF")
        # Conan can_run() alone can be true under binfmt; the x86 runner
        # cannot execute the dynamically linked OHOS delivery binary.
        if platform.machine() not in ("aarch64", "arm64"):
            self.output.warning("native OHOS functional test skipped on x86; QEMU static-object smoke only")
            return
        test_binary = os.path.join(self.build_folder, "test_xtail")
        self.run(f'"{test_binary}" "{executable}"', env="conanrun")
