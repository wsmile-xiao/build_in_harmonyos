#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class TinyexrConan(ConanFile):
    name = "tinyexr"
    version = "1.0.13"
    description = "Tiny OpenEXR image loader/saver library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/syoyo/tinyexr"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if bool(self.options.shared):
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tool(self, key, fallback):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        value = compilers.get(key)
        if value:
            return value
        c_dir = os.path.dirname(compilers.get("c", "") or compilers.get("cpp", ""))
        return os.path.join(c_dir, fallback) if c_dir else fallback

    def build(self):
        cc = self._tool("c", "clang")
        cxx = self._tool("cpp", "clang++")
        ar = self._tool("ar", "llvm-ar")
        pic = ["-fPIC"] if bool(self.options.get_safe("fPIC", True)) else []
        inc = ["-I", os.path.join(self.source_folder, "deps", "miniz")]
        cflags = ["-O2"] + pic + inc
        cxxflags = ["-O2", "-std=c++11"] + pic + inc

        if can_run(self):
            images = os.path.join(self.source_folder, "openexr-images")
            if not os.path.isdir(os.path.join(images, "ScanLines")):
                get(
                    self,
                    "https://codeload.github.com/AcademySoftwareFoundation/openexr-images/tar.gz/refs/heads/main",
                    destination=images,
                    filename="openexr-images-main.tar.gz",
                    strip_root=True,
                )
            replace_in_file(
                self,
                os.path.join(self.source_folder, "test", "unit", "tester.cc"),
                'const char* kOpenEXRImagePath = "../../../openexr-images/";',
                'const char* kOpenEXRImagePath = "../../openexr-images/";',
            )
            unit = os.path.join(self.source_folder, "test", "unit")
            self.run(
                'make CC="{}" CXX="{}" CFLAGS="{}" CXXFLAGS="{}" tester'.format(
                    cc, cxx, " ".join(["-O2"] + inc), " ".join(["-O2", "-std=c++11"] + inc)
                ),
                cwd=unit,
            )
            self.run("./tester", cwd=unit)
            self.run(
                '"{}" -O2 -std=c++11 -I../.. -o tester-v2 tester-v2.cc'.format(cxx),
                cwd=unit,
            )
            self.run("./tester-v2", cwd=unit)
            self.run(
                'make CC="{}" CXX="{}" CFLAGS="{}" CXXFLAGS_V3="{}" tester-v3'.format(
                    cc,
                    cxx,
                    " ".join(["-O2"] + inc),
                    " ".join(["-O2", "-std=c++17"] + inc),
                ),
                cwd=unit,
            )
            self.run("./tester-v3", cwd=unit)
            simd_cc = os.path.join(self.source_folder, "tinyexr_simd_wrapper.cc")
            self.run(
                '"{}" -std=c++17 -O2 -DTINYEXR_ENABLE_SIMD=1 -DTINYEXR_V3_USE_SIMD=1 '
                '-I../.. -o tester-v3-simd tester-v3-simd.cc "{}"'.format(cxx, simd_cc),
                cwd=unit,
            )
            self.run("./tester-v3-simd", cwd=unit)
            self.run(
                'make CC="{}" CXX="{}" CFLAGS="{}" CXXFLAGS="{}" test'.format(
                    cc, cxx, " ".join(["-O2"] + inc), " ".join(["-O2", "-std=c++11"] + inc)
                ),
                cwd=self.source_folder,
            )
            self.run(
                'make CC="{}" CXX="{}" CFLAGS="{}" CXXFLAGS_V3="{}" test-v3'.format(
                    cc,
                    cxx,
                    " ".join(["-O2"] + inc),
                    " ".join(["-O2", "-std=c++17"] + inc),
                ),
                cwd=self.source_folder,
            )

        miniz_c = os.path.join(self.source_folder, "deps", "miniz", "miniz.c")
        tiny_cc = os.path.join(self.source_folder, "tinyexr.cc")
        self.run(
            '"{}" {} -c "{}" -o miniz.o'.format(cc, " ".join(cflags), miniz_c),
            cwd=self.source_folder,
        )
        self.run(
            '"{}" {} -c "{}" -o tinyexr.o'.format(cxx, " ".join(cxxflags), tiny_cc),
            cwd=self.source_folder,
        )
        if bool(self.options.shared):
            self.run(
                '"{}" -shared -o libtinyexr.so tinyexr.o miniz.o -Wl,-soname,libtinyexr.so'.format(cxx),
                cwd=self.source_folder,
            )
        else:
            self.run(
                '"{}" rcs libtinyexr.a tinyexr.o miniz.o'.format(ar),
                cwd=self.source_folder,
            )

    def package(self):
        copy(
            self,
            "tinyexr.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        lib_name = "libtinyexr.so" if bool(self.options.shared) else "libtinyexr.a"
        copy(
            self,
            lib_name,
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["tinyexr"]
        self.cpp_info.set_property("cmake_file_name", "tinyexr")
        self.cpp_info.set_property("cmake_target_name", "tinyexr::tinyexr")
        if self.settings.os != "Windows":
            self.cpp_info.system_libs = ["m"]
