"""Headless consumer of the installed libQGLViewer library."""

import os
from pathlib import Path

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.env import Environment, VirtualRunEnv


class LibqglviewerTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        candidate = Path(self.build_folder, "qglviewer_consumer")
        if str(self.settings.os) == "OHOS":
            self.run(f'binary-sign-tool sign -inFile "{candidate}" '
                     f'-outFile "{candidate}.signed" -selfSign 1')
            os.replace(str(candidate) + ".signed", candidate)
            os.chmod(candidate, 0o755)
        environment = Environment()
        for dependency in self.dependencies.host.values():
            environment.prepend_path("LD_LIBRARY_PATH",
                                     os.path.join(dependency.package_folder, "lib"))
        qt = self.dependencies["qt5-qtbase"].package_folder
        environment.define("QT_QPA_PLATFORM", "offscreen")
        environment.define("QT_QPA_PLATFORM_PLUGIN_PATH",
                           os.path.join(qt, "plugins", "platforms"))
        with environment.vars(self).apply():
            self.run(f'"{candidate}"')
