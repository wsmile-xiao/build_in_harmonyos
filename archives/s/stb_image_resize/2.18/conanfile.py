from conan import ConanFile
from conan.tools.files import copy, get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
import os


class StbImageResize2Conan(ConanFile):
    name = "stb_image_resize"
    version = "2.18"
    description = "Image resizing library with SSE2, AVX, Neon and WASM SIMD support"
    license = ("MIT", "Unlicense")
    url = "https://github.com/nothings/stb"
    homepage = "https://github.com/nothings/stb"
    topics = ("image", "resize", "header-only")
    
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True
    package_type = "header-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version])

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "LICENSE", 
             src=self.source_folder, 
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "stb_image_resize2.h", 
             src=self.source_folder, 
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "stb_image_resize")
        self.cpp_info.set_property("cmake_target_name", "stb::image_resize")
        self.cpp_info.set_property("pkg_config_name", "stb_image_resize")
