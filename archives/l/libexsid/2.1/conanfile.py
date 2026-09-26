from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
import os


class LibexsidConan(ConanFile):
    name = "libexsid"
    version = "2.1"
    description = "I/O library for exSID USB"
    license = "GPL-2.0-only"
    homepage = "https://github.com/libsidplayfp/exsid-driver"
    url = "https://github.com/libsidplayfp/exsid-driver"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        copy(self, "CMakeLists.txt", src=os.path.join(self.recipe_folder, "cmake"),
             dst=os.path.join(self.export_sources_folder, "cmake"))
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libftdi/1.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, filename="exsid-driver-2.1.tar.gz", **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        # The upstream tag is source-only and its CI worker has no aclocal.
        # Supply a small CMake project from recipe sources instead of running
        # autoreconf on the worker.
        copy(self, "CMakeLists.txt", src=os.path.join(self.export_sources_folder, "cmake"),
             dst=self.source_folder)
        cmake = CMake(self)
        cmake.configure(variables={
            "LIBFTDI_INCLUDE_DIR": os.path.join(
                self.dependencies["libftdi"].package_folder, "include", "libftdi1"
            )
        })
        cmake.build()
        # Upstream declares no tests; keep the zero-test check explicit.
        cmake.build(target="check")

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["exsid"]
        self.cpp_info.set_property("cmake_file_name", "libexsid")
        self.cpp_info.set_property("cmake_target_name", "libexsid::libexsid")
        self.cpp_info.set_property("pkg_config_name", "libexsid")