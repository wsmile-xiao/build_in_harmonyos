"""libcvd image-processing library for OpenHarmony PC."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import copy, get


class LibcvdConan(ConanFile):
    name = "libcvd"
    version = "0.0-git20221020150751.30e8cfc"
    description = "Computer vision and image-processing library"
    license = "BSD-2-Clause"
    homepage = "https://github.com/edrosten/libcvd"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def requirements(self):
        self.requires("libjpeg-turbo/3.2.0")
        # 1.6.58 and libtiff/4.7.0 share zlib/1.3.1.1; 1.6.58.3 does not.
        self.requires("libpng/1.6.58")
        self.requires("libtiff/4.7.0")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CVD_ENABLE_TESTS"] = True
        tc.cache_variables["CVD_ENABLE_PROGS"] = False
        tc.cache_variables["CVD_ENABLE_EXAMPLES"] = False
        tc.cache_variables["CVD_ENABLE_OPENCV_TESTS"] = False
        tc.cache_variables["CVD_INTERNAL_GLOB_IS_BAD"] = True
        tc.cache_variables["CVD_HAVE_V4L"] = False
        tc.cache_variables["CVD_HAVE_UVC"] = False
        tc.cache_variables["CVD_FFMPEG_FOUND"] = False
        tc.cache_variables["CVD_TooN_FOUND"] = False
        tc.cache_variables["CVD_dc1394v2_FOUND"] = False
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_X11"] = True
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_OpenGL"] = True
        # The upstream project calls FindJPEG/PNG/TIFF directly. Point each
        # finder at the exact Conan binary rather than probing the host SDK.
        for name, prefix, library in (
            ("libjpeg-turbo", "JPEG", "libjpeg.so"),
            ("libpng", "PNG", "libpng.so"),
            ("libtiff", "TIFF", "libtiff.so"),
            ("zlib", "ZLIB", "libz.a"),
        ):
            folder = self.dependencies[name].package_folder
            include = os.path.join(folder, "include")
            lib = os.path.join(folder, "lib", library)
            if prefix == "PNG":
                tc.cache_variables["PNG_PNG_INCLUDE_DIR"] = include
            else:
                tc.cache_variables[prefix + "_INCLUDE_DIR"] = include
            tc.cache_variables[prefix + "_LIBRARY"] = lib
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
            if can_run(self):
                self.run("ctest --output-on-failure -j1", cwd=self.build_folder,
                         env="conanrun")

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["cvd"]
        self.cpp_info.set_property("cmake_file_name", "libcvd")
        self.cpp_info.set_property("cmake_target_name", "libcvd::libcvd")
