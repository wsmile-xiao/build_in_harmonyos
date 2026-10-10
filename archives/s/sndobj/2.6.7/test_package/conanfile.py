import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class SndobjTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

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
        executable = os.path.join(self.build_folder, "sndobj_consumer")
        if str(self.settings.os) == "Windows":
            executable += ".exe"
        if str(self.settings.os) == "OHOS":
            signer = shutil.which("binary-sign-tool")
            if not signer:
                raise ConanInvalidConfiguration("binary-sign-tool is required on OHOS")
            signed = executable + ".signed"
            subprocess.run([signer, "sign", "-inFile", executable,
                            "-outFile", signed, "-selfSign", "1"],
                           check=True, capture_output=True, text=True, timeout=40)
            os.chmod(signed, os.stat(executable).st_mode)
            os.replace(signed, executable)
        self.run('"{}"'.format(executable), env="conanrun")
