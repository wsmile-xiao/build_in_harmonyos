from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
import os


class UnittestCppConan(ConanFile):
    name = "unittest-cpp"
    version = "2.0.0"
    description = "Lightweight C++ unit testing framework"
    license = "MIT"
    homepage = "https://github.com/unittest-cpp/unittest-cpp"
    url = "https://github.com/unittest-cpp/unittest-cpp"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["UTPP_INCLUDE_TESTS_IN_BUILD"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        test_exe = os.path.join(self.build_folder, "TestUnitTest++")
        self.run(test_exe, env="conanrun")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["UnitTest++"]
