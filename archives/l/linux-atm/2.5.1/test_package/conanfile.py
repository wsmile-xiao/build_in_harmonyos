import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LinuxAtmTestConan(ConanFile):
    """test_package for linux-atm: builds a libatm consumer and, on OHOS,
    additionally checks that the packaged CLI tools are runnable AArch64 ELF
    binaries (HarmonyOS specific smoke test)."""

    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return

        cmake = CMake(self)
        cmake.test()

        # HarmonyOS specific: the packaged tools must be runnable aarch64 ELF
        # binaries and must report the linux-atm version.
        deps = self.dependencies[self.tested_reference_str]
        tool = None
        for bindir in deps.cpp_info.bindirs:
            candidate = os.path.join(bindir, "atmsigd")
            if os.path.isfile(candidate):
                tool = candidate
                break
        if tool is None:
            raise ConanException("atmsigd was not installed by the package")

        with open(tool, "rb") as fh:
            elf = fh.read(20)
        if elf[:4] != b"\x7fELF":
            raise ConanException("atmsigd is not an ELF executable")
        machine = int.from_bytes(elf[18:20], "little")
        if machine != 183:  # EM_AARCH64
            raise ConanException(
                "atmsigd is not an AArch64 binary (e_machine=%d)" % machine)

        self.output.info("OHOS smoke test: %s -V" % tool)
        self.run('"%s" -V' % tool, env="conanrun")
