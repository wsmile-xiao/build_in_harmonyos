from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
import os


class MedTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Declare hdf5 as a direct requirement too: CMakeDeps only generates a
        # <pkg>-config.cmake for direct requirements, and the upstream MED config
        # does not propagate hdf5 via find_dependency. Without this, the consumer
        # CMakeLists' `find_package(hdf5 REQUIRED)` (needed for med.h's <hdf5.h>)
        # cannot locate hdf5-config.cmake. Version must match the one med uses.
        self.requires("hdf5/1.14.6")

    def configure(self):
        # The tested med package forces hdf5 + libaec static (OHOS loader cannot
        # dlopen user-path .so; the consumer test_med is built fully static and
        # runs natively). The test_package graph must resolve the SAME static
        # hdf5/libaec variants, otherwise find_package(medfile) -> the medfile
        # config's hdf5 dependency cannot locate a matching hdf5-config.cmake.
        if self.settings.os == "OHOS":
            self.options["hdf5"].shared = False
            self.options["libaec"].shared = False

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Generators are produced here (not via the `generators` attribute) so the
        # OHOS system name / aarch64 processor are injected for the test build too.
        tc = CMakeToolchain(self)
        tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
        tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        # Compiling + linking the consumer exercises the full public surface of the
        # package: medfile CMake config, med.h (which transitively pulls hdf5.h),
        # the exported static target and the hdf5 dependency. On OHOS the binary is
        # fully static (medC.a + hdf5.a + libaec.a), so it runs natively — this is
        # the required HarmonyOS-specific end-to-end consumer test (rule12).
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # On OHOS the binary is fully static, so it needs no user-path .so and runs
        # natively without any runtime env. On other platforms run it through the
        # conanrun env so the shared libs are on the loader path.
        if self.settings.os == "OHOS":
            self.run(os.path.join(self.cpp.build.bindir, "test_med"))
        else:
            self.run(os.path.join(self.cpp.build.bindir, "test_med"), env="conanrun")
