from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
import os


class MinctestConan(ConanFile):
    name = "minctest"
    version = "0.3.0"
    description = "Minimal unit-testing framework for C"
    license = "Zlib"
    url = "https://github.com/codeplea/minctest"
    homepage = "https://codeplea.com/minctest"
    topics = ("testing", "unit-testing", "header-only")
    
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True
    
    @property
    def _min_cppstd(self):
        return 11
    
    def export_sources(self):
        export_conandata_patches(self)
    
    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
    
    def build(self):
        pass  # Header-only library
    
    def package_id(self):
        self.info.clear()
    
    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "minctest.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
    
    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
