"""Run the packaged QDirStat executable through its public CLI."""

import platform

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class QDirStatTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self) and platform.system() == "HarmonyOS":
            env = Environment()
            env.define("QT_QPA_PLATFORM", "offscreen")
            with env.vars(self).apply():
                self.run(
                    'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                        self.build_folder
                    ),
                    env=["conanbuild", "conanrun"],
                )
            self.output.info("QDIRSTAT_CONSUMER_PASS")
