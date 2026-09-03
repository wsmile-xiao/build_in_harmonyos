from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class LibSnowConan(ConanFile):
    name = "libsnow"
    version = "2.3.2"
    description = "A testing library for C"
    license = "MIT"
    url = "https://github.com/mortie/snow"
    homepage = "https://github.com/mortie/snow"
    topics = ("testing", "unit-testing", "c", "header-only")
    
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True
    
    def export_sources(self):
        export_conandata_patches(self)
    
    def layout(self):
        basic_layout(self, src_folder="src")
    
    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Conan strips the top-level directory, so patch paths should be relative to src/
        # Patch expects snow-2.3.2/snow/snow.h, but Conan has src/snow/snow.h
        # We need to create the expected directory structure for the patch
        import shutil
        import os
        src_dir = os.path.join(self.source_folder, "snow-2.3.2")
        if not os.path.exists(src_dir):
            # Move everything to snow-2.3.2/ subdirectory
            temp_dir = os.path.join(self.source_folder, "temp_snow")
            os.makedirs(temp_dir, exist_ok=True)
            for item in os.listdir(self.source_folder):
                if item not in ["temp_snow", "snow-2.3.2"]:
                    shutil.move(
                        os.path.join(self.source_folder, item),
                        os.path.join(temp_dir, item)
                    )
            shutil.move(temp_dir, src_dir)
    
    def build(self):
        apply_conandata_patches(self)
    
    def package(self):
        copy(self, "LICENSE", src=os.path.join(self.source_folder, "snow-2.3.2"), dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "snow-2.3.2", "snow"), 
             dst=os.path.join(self.package_folder, "include", "snow"))
    
    def package_id(self):
        self.info.clear()
    
    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libsnow")
        self.cpp_info.set_property("cmake_target_name", "libsnow::libsnow")
