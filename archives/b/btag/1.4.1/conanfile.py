#!/usr/bin/env python3
"""Conan recipe for btag 1.4.1, a command-line batch audio tagger."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class BtagConan(ConanFile):
    name = "btag"
    version = "1.4.1"
    description = "Command-line audio file tagger with batch editing and filename normalization"
    license = "BSD-2-Clause"
    homepage = "https://github.com/fernandotcl/btag"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.84.0")
        self.requires("libedit/20240808")
        self.requires("taglib/1.13.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["BOOST_LOCALE_SUPPORT"] = False
        tc.variables["CUESHEET_SUPPORT"] = False
        tc.variables["ENABLE_TESTS"] = True

        # btag ships FindTagLib/FindLibEdit modules. Point their legacy cache
        # variables at Conan packages and select static archives explicitly;
        # otherwise find_library may pick libedit.so and leak a build-cache
        # runtime dependency into the installed command.
        libedit = self.dependencies["libedit"]
        taglib = self.dependencies["taglib"]
        tc.cache_variables["LIBEDIT_INCLUDE_DIR"] = libedit.cpp_info.includedirs[0]
        tc.cache_variables["LIBEDIT_LIBRARY"] = os.path.join(
            libedit.cpp_info.libdirs[0], "libedit.a"
        )
        tc.cache_variables["TAGLIB_INCLUDE_DIR"] = taglib.cpp_info.includedirs[0]
        tc.cache_variables["TAGLIB_LIBRARY"] = os.path.join(
            taglib.cpp_info.libdirs[0], "libtag.a"
        )
        zlib = self.dependencies["zlib"]
        # The OHOS image provides only the versioned runtime library
        # /usr/lib/libtinfo.so.6 (there is no libtinfo.so linker symlink).
        # Naming it explicitly avoids CMake emitting an unresolvable -ltinfo.
        if self.settings.os == "OHOS":
            terminal_lib = "/usr/lib/libtinfo.so.6"
        elif self.settings.os == "Linux":
            terminal_lib = "tinfo"
        else:
            terminal_lib = "curses"
        tc.cache_variables["EXTRA_LIBRARIES"] = ";".join(
            [os.path.join(zlib.cpp_info.libdirs[0], "libz.a"), "m", terminal_lib]
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream registers exactly two CTest cases. Keep both enabled and
        # execute them as part of the package build.
        cmake.test()

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
