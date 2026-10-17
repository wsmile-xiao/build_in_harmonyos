from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
import os


class LiblercConan(ConanFile):
    name = "liblerc"
    version = "4.2.0"
    description = "Limited Error Raster Compression library"
    license = "Apache-2.0"
    url = "https://github.com/Esri/lerc"
    homepage = "https://github.com/Esri/lerc"
    topics = ("compression", "raster", "image", "lerc", "esri")
    
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    
    def export_sources(self):
        copy(self, "conandata.yml", self.recipe_folder, self.export_sources_folder)
    
    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
    
    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
    
    def layout(self):
        cmake_layout(self, src_folder="src")
    
    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
    
    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()
    
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
    
    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
    
    def package_info(self):
        self.cpp_info.libs = ["Lerc"]
        self.cpp_info.set_property("pkg_config_name", "Lerc")
        
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
        
        if not self.options.shared:
            self.cpp_info.defines.append("LERC_STATIC")
