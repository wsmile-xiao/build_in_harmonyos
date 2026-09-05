from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get
import os


class LestConan(ConanFile):
    name = "lest"
    version = "1.37.0"
    description = "A modern C++ unit-test, TDD and BDD framework"
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/lest"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": True}

    def export_sources(self):
        copy(self, "conandata.yml", dst=".", src=self.recipe_folder)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["LEST_BUILD_TEST"] = bool(self.options.run_upstream_tests)
        # The examples intentionally contain failing tests; they are teaching
        # programs, not a passing library regression suite.
        tc.variables["LEST_BUILD_EXAMPLE"] = False
        tc.variables["LEST_BUILD_CONTRIB"] = False
        tc.variables["LEST_EXTRA_WARNINGS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.run_upstream_tests:
            self.run("ctest -L unittest --output-on-failure", cwd=self.build_folder)

    def package(self):
        copy(self, "*.hpp", dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.source_folder, "include"))
        copy(self, "LICENSE.txt", dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "lest")
        self.cpp_info.set_property("cmake_target_name", "lest::lest")
