"""test_package for libsmacker — consumer assertion test (R34).

Flow
  1. gen_smk.py writes `synthetic.smk` (8x8 / 1 frame / video only /
     solid colour 0x20) into the build folder — no network, no committed
     binary fixture.
  2. ./libsmacker_test synthetic.smk links against the *installed* package
     and asserts on smk_open_*/smk_info_*/smk_enable_*/smk_first/
     smk_get_*/smk_close plus the driver.c BMP dump path.
  3. Non-zero exit from the binary fails `conan create`.
"""
import os
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibsmackerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

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
        gen = os.path.join(self.recipe_folder, "gen_smk.py")
        if not os.path.isfile(gen):
            raise Exception("gen_smk.py missing next to this conanfile: %s"
                            % gen)
        # sys.executable: OHOS' python does not PATH-search bare command
        # names in subprocesses (device-facts §一.14).
        self.run('"%s" "%s" synthetic.smk' % (sys.executable, gen))
        # default cwd for self.run is self.build_folder, where CMake put the
        # binary and where gen_smk.py just wrote synthetic.smk.
        self.run("./libsmacker_test synthetic.smk", env="conanrun")
