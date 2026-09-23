from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os


class LibasdConan(ConanFile):
    name = "libasd"
    version = "1.5.6"
    description = "C++11 header-only library for reading high-speed AFM ASD files"
    license = "MIT"
    homepage = "https://github.com/ToruNiina/libasd"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "conandata.yml"

    def export_sources(self):
        copy(self, "conandata.yml", dst=".", src=self.recipe_folder)
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Keep the recipe patch contract explicit even when this release needs no patch.
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "libasd"),
             dst=os.path.join(self.package_folder, "include", "libasd"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libasd")
        self.cpp_info.set_property("cmake_target_name", "libasd::libasd")
