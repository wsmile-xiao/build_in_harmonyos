import os
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class ZitaAlsaPcmiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # The published alsa-lib recipe omits cpp_info.includedirs, so the
        # alsa headers (<alsa/asoundlib.h>, pulled in by zita-alsa-pcmi.h)
        # are not propagated by CMakeDeps. Inject the include dir explicitly.
        alsa = self.dependencies["alsa-lib"]
        tc.variables["ALSA_INCLUDE_DIR"] = os.path.join(alsa.package_folder, "include")
        tc.variables["ALSA_LIB_DIR"] = os.path.join(alsa.package_folder, "lib")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # cmake_layout places the executable in the build folder root
            # (no RUNTIME_OUTPUT_DIRECTORY configured).
            executable = Path(self.build_folder) / "test_zita-alsa-pcmi"
            self.run('"{}"'.format(executable), env="conanrun")
