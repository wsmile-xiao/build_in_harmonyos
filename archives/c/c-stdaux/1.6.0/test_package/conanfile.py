import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class CStdauxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

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
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Skipping c-stdaux_test: target binary cannot run here")
            return
        exe = os.path.join(self.build_folder, "c-stdaux_test")
        if str(self.settings.os) == "Windows":
            exe += ".exe"
            self.run(f'"{exe}"', env="conanrun")
            return
        if str(self.settings.os) == "OHOS":
            shell = os.environ.get("CONFIG_SHELL")
            if not shell:
                shell = "/usr/bin/zsh" if os.path.exists("/usr/bin/zsh") else "/system/bin/sh"
            self.run(f"{shlex.quote(shell)} -c {shlex.quote(shlex.quote(exe))}", env="conanrun")
            return
        self.run(shlex.quote(exe), env="conanrun")
