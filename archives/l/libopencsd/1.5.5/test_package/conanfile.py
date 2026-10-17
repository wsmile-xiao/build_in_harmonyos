import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LibopencsdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L1 consumer: link against the packaged libs and exercise the C API.
        self.run("./ocsd_consumer", env="conanrun")
        # HarmonyOS-specific checks (ELF target/SONAME + dlopen of the
        # packaged shared library). Runs the dlopen check on every platform;
        # the ELF checks are gated to OHOS where they are meaningful.
        pkg = self.dependencies["libopencsd"]
        libdir = os.path.join(pkg.package_folder, "lib")
        self.run(f"bash test_ohos.sh {libdir} {self.settings.os} ./ocsd_dlopen",
                 env="conanrun")
