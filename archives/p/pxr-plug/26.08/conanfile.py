from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class PxrPlugConan(ConanFile):
    name = "pxr-plug"
    version = "26.08"
    description = "Plugin framework library from Pixar OpenUSD (Universal Scene Description)"
    license = "Modified Apache 2.0 License"
    homepage = "https://openusd.org"
    url = "https://github.com/PixarAnimationStudios/OpenUSD"
    topics = ("openusd", "pixar", "plugin", "pxr", "3d", "scene-description")
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

    exports_sources = "patches/*"

    def requirements(self):
        self.requires("tbb/2023.0.0")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm("fPIC")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["PXR_BUILD_IMAGING"] = False
        tc.variables["PXR_BUILD_USD_IMAGING"] = False
        tc.variables["PXR_BUILD_USDVIEW"] = False
        tc.variables["PXR_BUILD_TESTS"] = False
        tc.variables["PXR_BUILD_EXAMPLES"] = False
        tc.variables["PXR_BUILD_TUTORIALS"] = False
        tc.variables["PXR_BUILD_USD_TOOLS"] = False
        tc.variables["PXR_ENABLE_PYTHON_SUPPORT"] = False
        tc.variables["PXR_BUILD_EXEC"] = False
        tc.variables["PXR_BUILD_USD_VALIDATION"] = False
        tc.variables["PXR_BUILD_USD"] = False
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Python"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Python3"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="plug")

    def package(self):
        lib_dir = os.path.join(self.build_folder, "lib")
        for libname in ["plug", "arch", "tf", "js", "trace", "work"]:
            copy(self, f"lib{libname}*", src=lib_dir, dst=os.path.join(self.package_folder, "lib"))
        include_base = os.path.join(self.source_folder, "pxr", "base")
        for libname in ["plug", "arch", "tf", "js", "trace", "work"]:
            src_include = os.path.join(include_base, libname)
            if os.path.isdir(src_include):
                copy(self, "*.h", src=src_include,
                     dst=os.path.join(self.package_folder, "include", "pxr", "base", libname))
        gen_include = os.path.join(self.build_folder, "include")
        if os.path.isdir(gen_include):
            copy(self, "*.h", src=gen_include,
                 dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["plug", "arch", "tf", "js", "trace", "work"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["tbb::tbb"]
