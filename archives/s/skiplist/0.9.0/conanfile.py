from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.cmake import CMakeDeps, CMakeToolchain
import os


class SkiplistConan(ConanFile):
    name = "skiplist"
    version = "0.9.0"
    description = "A skiplist-based ordered collection library"
    license = "ISC"
    homepage = "https://github.com/silentbicycle/skiplist"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        copy(self, "conandata.yml", dst=".", src=self.recipe_folder)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        compiler = (self.conf.get("tools.build:compiler_executables", default={},
                                   check_type=dict) or {}).get("c", "cc")
        self.run(f"make CC={compiler} libskiplist.a test_skiplist", cwd=self.source_folder)
        self.run("./test_skiplist", cwd=self.source_folder)

    def package(self):
        copy(self, "libskiplist.a", dst=os.path.join(self.package_folder, "lib"),
             src=self.source_folder)
        copy(self, "skiplist.h", dst=os.path.join(self.package_folder, "include"),
             src=self.source_folder)
        copy(self, "skiplist_config.h", dst=os.path.join(self.package_folder, "include"),
             src=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["skiplist"]
        self.cpp_info.set_property("cmake_file_name", "skiplist")
        self.cpp_info.set_property("cmake_target_name", "skiplist::skiplist")
