import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OdpiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        build_type = str(self.settings.build_type)
        self.run(
            f"ctest --output-on-failure --build-config {build_type}",
            env="conanrun",
        )
        odpi_pkg = self.dependencies["odpi"].package_folder
        library_path = os.path.join(odpi_pkg, "lib", "libodpic.so.6.0.0")
        test_script = os.path.join(self.source_folder, "test_ohos.py")
        self.run(f'python3 "{test_script}" "{library_path}"')