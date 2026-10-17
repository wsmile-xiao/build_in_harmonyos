from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import collect_libs, copy, get
import os


class ImathConan(ConanFile):
    name = "imath"
    version = "3.2.2"
    package_type = "library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/AcademySoftwareFoundation/Imath"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["PYTHON"] = False
        tc.variables["PYBIND11"] = False
        tc.variables["BUILD_WEBSITE"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        CMake(self).install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Imath")
        self.cpp_info.set_property("pkg_config_name", "Imath")
        component = self.cpp_info.components["imath"]
        component.libs = collect_libs(self)
        component.set_property("cmake_target_name", "Imath::Imath")
        component.set_property("pkg_config_name", "Imath")
