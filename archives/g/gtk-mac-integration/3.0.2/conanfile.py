#!/usr/bin/env python3
"""Conan recipe for the gtk-mac-integration 3.0.2 compatibility API."""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class GtkMacIntegrationConan(ConanFile):
    name = "gtk-mac-integration"
    version = "3.0.2"
    description = "Portable compatibility layer for the gtk-mac-integration API"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gtk-mac-integration"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "the compatibility backend supports Linux and OHOS"
            )

    def requirements(self):
        self.requires("glib/2.84.0")

    def _source_entries(self):
        data = dict(self.conan_data["sources"])
        urls = data.pop("url")
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            entry = dict(data)
            entry["url"] = url
            yield entry

    def source(self):
        last_error = None
        for source in self._source_entries():
            try:
                self.output.info(f"Downloading source from {source['url']}")
                get(self, **source, strip_root=True)
                return
            except ConanException as exc:
                last_error = exc
                self.output.warning(f"Source download failed from {source['url']}: {exc}")
        raise last_error

    def export_sources(self):
        copy(
            self,
            "*",
            src=os.path.join(self.recipe_folder, "ohos"),
            dst=os.path.join(self.export_sources_folder, "ohos"),
        )

    def layout(self):
        cmake_layout(self)

    def _glib_include_dirs(self):
        glib_folder = self.dependencies["glib"].package_folder
        return [
            os.path.join(glib_folder, "include", "glib-2.0").replace("\\", "/"),
            os.path.join(glib_folder, "lib", "glib-2.0", "include").replace(
                "\\", "/"
            ),
        ]

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        glib_include_dir, glib_config_include_dir = self._glib_include_dirs()
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.fPIC
        tc.variables["GLIB_INCLUDE_DIR"] = glib_include_dir
        tc.variables["GLIB_CONFIG_INCLUDE_DIR"] = glib_config_include_dir
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(
            build_script_folder=os.path.join(self.export_sources_folder, "ohos")
        )
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["gtkmacintegration-gtk3"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "gtk-mac-integration")
        self.cpp_info.set_property(
            "cmake_target_name", "gtk-mac-integration::gtk-mac-integration"
        )
        self.cpp_info.set_property("pkg_config_name", "gtk-mac-integration-gtk3")
        self.cpp_info.defines = ["GTKOSX_HARMONYOS_COMPAT=1"]
        self.cpp_info.requires = ["glib::glib"]
