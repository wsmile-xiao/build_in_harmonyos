#!/usr/bin/env python3
"""Conan recipe — lwbtn 1.3.2 (MaJerle lightweight button manager).

CMake library: `lwbtn/library.cmake` registers target `lwbtn`
(single source lwbtn.c, public include dirs src/include + generated
lib_inc). Upstream provides no install() rules, so packaging is done
manually: copy the built static lib and the public headers
(lwbtn.h, lwbtn_opt.h + the configure_file-generated lwbtn_opts.h).

R32: recipe accepts os in ("Linux", "OHOS").
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class LwbtnConan(ConanFile):
    name = "lwbtn"
    version = "1.3.2"
    description = "lwbtn — lightweight button manager for embedded systems"
    license = "MIT"
    homepage = "https://github.com/MaJerle/lwbtn"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if not self.options.shared:
            tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Only the library target — skip the upstream test executables
        cmake.build(target="lwbtn")

    def package(self):
        # Upstream has no install() rules → manual packaging
        copy(self, "liblwbtn.a", src=os.path.join(self.build_folder, "tests", "lwbtn"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "lwbtn", "src", "include", "lwbtn"),
             dst=os.path.join(self.package_folder, "include", "lwbtn"))
        # configure_file-generated lwbtn_opts.h lives in lib_inc
        copy(self, "lwbtn_opts.h", src=os.path.join(self.build_folder, "tests", "lwbtn", "lib_inc"),
             dst=os.path.join(self.package_folder, "include", "lwbtn"))

    def package_info(self):
        self.cpp_info.libs = ["lwbtn"]
        self.cpp_info.set_property("cmake_file_name", "lwbtn")
        self.cpp_info.set_property("cmake_target_name", "lwbtn::lwbtn")
        self.cpp_info.includedirs = ["include"]