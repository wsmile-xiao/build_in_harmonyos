from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout
import os


class MunitConan(ConanFile):
    name = "munit"
    version = "0.4.1"
    description = "µnit is a small but full-featured unit testing framework for C"
    license = "MIT"
    homepage = "https://nemequ.github.io/munit/"
    url = "https://github.com/conan-io/conan-center-index"
    topics = ("testing", "unit-testing", "c")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # munit is a header-only style library that can be compiled directly
        # No build step needed - just copy sources

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "munit.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "munit.c", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        # munit is typically compiled directly into the test executable
        # Users should compile munit.c with their test code
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        
        # No actual library to link, users compile munit.c directly
        # But we need to provide the include path
        self.cpp_info.libs = []
        
        # Set the source file path for consumers
        self.cpp_info.set_property("cmake_file_name", "munit")
        self.cpp_info.set_property("cmake_target_name", "munit::munit")
        self.cpp_info.set_property("cmake_find_mode", "both")
