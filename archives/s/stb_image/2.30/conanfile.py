from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout
import os


class StbImageConan(ConanFile):
    name = "stb_image"
    version = "2.30"
    description = "Image loading/decoding from file/memory: JPG, PNG, TGA, BMP, PSD, GIF, HDR, PIC"
    license = ("MIT", "Unlicense")
    url = "https://github.com/nothings/stb"
    homepage = "https://github.com/nothings/stb"
    topics = ("image", "loader", "header-only")
    
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True
    package_type = "header-library"

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version])

    def package(self):
        copy(self, "LICENSE", 
             src=self.source_folder, 
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "stb_image.h", 
             src=self.source_folder, 
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "stb_image")
        self.cpp_info.set_property("cmake_target_name", "stb::image")
        self.cpp_info.set_property("pkg_config_name", "stb_image")
