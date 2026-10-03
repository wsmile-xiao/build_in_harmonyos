import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Libam7xxxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "consumer.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"] if str(self.settings.os) == "OHOS" else None)

    def test(self):
        if not can_run(self):
            return
        executable = os.path.join(self.cpp.build.bindir, "libam7xxx_consumer")
        if str(self.settings.os) == "OHOS":
            signer = shutil.which("binary-sign-tool")
            if not signer:
                raise ConanException("binary-sign-tool is required on OHOS")
            signed = executable + ".signed"
            subprocess.run([signer, "sign", "-inFile", executable,
                            "-outFile", signed, "-selfSign", "1"], check=True)
            os.replace(signed, executable)
            os.chmod(executable, 0o755)
        self.run(f'"{executable}"', env="conanrun")
