#!/usr/bin/env python3
"""Conan recipe for the Qhull 2020.2 CMake reentrant shared library."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)


class QhullConan(ConanFile):
    name = "qhull"
    version = "2020.2"
    description = "Convex hull, Delaunay triangulation, and Voronoi library"
    license = "Qhull"
    homepage = "https://github.com/qhull/qhull"
    url = "https://github.com/qhull/qhull"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Qhull supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        is_ohos = str(self.settings.os) == "OHOS"
        tc.cache_variables["BUILD_SHARED_LIBS"] = True
        tc.cache_variables["BUILD_STATIC_LIBS"] = is_ohos
        tc.cache_variables["LINK_APPS_SHARED"] = not is_ohos
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        # CMake 4 removed the compatibility mode required by Qhull 2020.2.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not can_run(self):
            self.output.info(
                "cross-building: upstream CTest executables compiled but cannot run"
            )
        else:
            cmake.ctest(cli_args=["--output-on-failure", "--no-tests=error"])

    def package(self):
        copy(
            self,
            "COPYING.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.a", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "include", "libqhull"))
        rmdir(self, os.path.join(self.package_folder, "include", "libqhullcpp"))

    def package_info(self):
        component = self.cpp_info.components["qhull_r"]
        component.libs = ["qhull_r"]
        component.system_libs = ["m"]
        component.set_property("cmake_target_name", "Qhull::qhull_r")
        component.set_property("pkg_config_name", "qhull_r")
        self.cpp_info.set_property("cmake_file_name", "Qhull")
