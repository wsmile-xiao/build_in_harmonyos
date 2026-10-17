from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import get, copy, rmdir, apply_conandata_patches, export_conandata_patches
import os


class KodiToolsConan(ConanFile):
    name = "kodi-tools"
    version = "21.3"
    license = "GPL-2.0-or-later"
    url = "https://kodi.tv"
    description = "Kodi build tools (TexturePacker and JsonSchemaBuilder)"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"
    
    def requirements(self):
        self.requires("lzo/2.10")
        self.requires("libpng/1.6.58.2")
        self.requires("giflib/5.2.2")
        self.requires("libjpeg/10")
    
    def export_sources(self):
        export_conandata_patches(self)
    
    def layout(self):
        cmake_layout(self, src_folder="src")
    
    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
    
    def generate(self):
        tc = CMakeToolchain(self)
        # NOTE: do NOT set ENABLE_STATIC — Conan deps are shared libs (.so),
        # and ENABLE_STATIC restricts CMAKE_FIND_LIBRARY_SUFFIXES to .a only
        tc.variables["KODI_SOURCE_DIR"] = self.source_folder
        # TARGET_POSIX: kodi platform macro; without it cmdlineargs.h pulls windows.h
        tc.preprocessor_definitions["TARGET_POSIX"] = "1"
        tc.generate()
        
        # Generate CMake find_package() files for dependencies
        deps = CMakeDeps(self)
        # Workaround: libpng package declares 'png16' but CMake expects 'png'
        # The actual library file is libpng16.so with a symlink libpng.so
        deps.set_property("libpng", "cmake_find_mode", "both")
        deps.generate()
    
    def build(self):
        # Build TexturePacker
        cmake_tp = CMake(self)
        cmake_tp.configure(build_script_folder=os.path.join(self.source_folder, "tools/depends/native/TexturePacker/src"))
        cmake_tp.build()
        
        # Build JsonSchemaBuilder — wipe TexturePacker's CMake cache first,
        # because both projects would share the same build folder and CMake
        # rejects a source-dir change with a stale cache.
        build_dir = os.path.join(self.build_folder)
        rmdir(self, os.path.join(build_dir, "CMakeFiles"))
        if os.path.exists(os.path.join(build_dir, "CMakeCache.txt")):
            os.remove(os.path.join(build_dir, "CMakeCache.txt"))
        cmake_jsb = CMake(self)
        cmake_jsb.configure(build_script_folder=os.path.join(self.source_folder, "tools/depends/native/JsonSchemaBuilder/src"))
        cmake_jsb.build()
    
    def package(self):
        copy(self, "LICENSE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "TexturePacker", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "JsonSchemaBuilder", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
    
    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
