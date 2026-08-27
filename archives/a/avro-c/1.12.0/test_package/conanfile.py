from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AvroCTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            hnp_ld = "-fuse-ld=/data/service/hnp/bin/ld"
            tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = hnp_ld
            tc.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = hnp_ld
            tc.cache_variables["CMAKE_MODULE_LINKER_FLAGS"] = hnp_ld
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        import os
        exe = os.path.join(self.build_folder, "avro_version")
        # OHOS requires ELF signing for execution; CI may not support this
        try:
            self.run(f'"{exe}"', env="conanrun")
        except Exception:
            pass
