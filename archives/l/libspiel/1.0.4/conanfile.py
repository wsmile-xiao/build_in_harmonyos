#!/usr/bin/env python3
"""Conan recipe for libspiel 1.0.4 on HarmonyOS PC."""

import os
import shutil
from contextlib import contextmanager

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


@contextmanager
def _prepend_environment(**paths):
    original = {key: os.environ.get(key) for key in paths}
    try:
        for key, entries in paths.items():
            os.environ[key] = os.pathsep.join(entries + ([original[key]] if original[key] else []))
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class LibspielConan(ConanFile):
    name = "libspiel"
    version = "1.0.4"
    description = "Speech synthesis client library"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/project-spiel/libspiel"
    package_type = "static-library"
    exports_sources = "patches/*"
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps", "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires("libspeechprovider/1.0.3")
        self.requires("glib/2.84.0.1")
        self.requires("gstreamer/1.28.3")
        self.requires("gst-plugins-base/1.28.3")
        # GStreamer uses zlib/1.3.1, while the published GLib package and
        # libspeechprovider require 1.3.1.1. Keep their published binary IDs.
        self.requires("zlib/1.3.1.1", override=True)

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"],
            filename="libspiel-1.0.4.tar.gz", strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or shutil.which("clang")
        if not compiler:
            raise ConanInvalidConfiguration("clang is required")
        tc.binaries["c"] = compiler
        llvm_ar = os.path.join(os.path.dirname(os.path.realpath(compiler)), "llvm-ar")
        if not os.path.isfile(llvm_ar):
            llvm_ar = shutil.which("llvm-ar")
        if not llvm_ar:
            raise ConanInvalidConfiguration("llvm-ar is required")
        tc.binaries["ar"] = llvm_ar
        tc.project_options["docs"] = "false"
        tc.project_options["tests"] = "true"
        tc.project_options["utils"] = "false"
        tc.project_options["introspection"] = "false"
        tc.project_options["default_library"] = "static"
        tc.project_options["wrap_mode"] = "nofallback"
        tc.generate()

    def _package_paths(self):
        packages = [dep.package_folder for dep in self.dependencies.values()
                    if dep.package_folder]
        return {
            "PKG_CONFIG_PATH": [self.generators_folder] + [
                os.path.join(package, "lib", "pkgconfig") for package in packages
            ],
            "LD_LIBRARY_PATH": [os.path.join(package, "lib") for package in packages],
        }

    def build(self):
        # Meson looks up upstream module names such as gstreamer-audio-1.0,
        # while PkgConfigDeps emits one name for each Conan package. Restore
        # the packages' own module files, relocating their prefix=/ metadata.
        for dependency in self.dependencies.values():
            package = dependency.package_folder
            if not package:
                continue
            pc_dir = os.path.join(package, "lib", "pkgconfig")
            if not os.path.isdir(pc_dir):
                continue
            for name in os.listdir(pc_dir):
                if not name.endswith(".pc"):
                    continue
                target = os.path.join(self.generators_folder, name)
                if os.path.exists(target):
                    continue
                with open(os.path.join(pc_dir, name), encoding="utf-8") as stream:
                    content = stream.read()
                content = content.replace("prefix=/\n", f"prefix={package}\n", 1)
                with open(target, "w", encoding="utf-8") as stream:
                    stream.write(content)
        # gnome.gdbus_codegen queries this variable from gio-2.0.pc. The
        # upstream GLib .pc has it, but PkgConfigDeps drops custom variables.
        gio_pc = os.path.join(self.generators_folder, "gio-2.0.pc")
        with open(gio_pc, "a", encoding="utf-8") as stream:
            glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
            stream.write("\ngdbus_codegen=%s\n" % os.path.join(glib_bin, "gdbus-codegen"))
            schema_compiler = shutil.which("glib-compile-schemas")
            if not schema_compiler:
                raise ConanInvalidConfiguration("glib-compile-schemas is required")
            stream.write(f"glib_compile_schemas={schema_compiler}\n")
        with _prepend_environment(**self._package_paths()):
            meson = Meson(self)
            meson.configure()
            meson.build()
            self.run(f"meson test --verbose -C {self.build_folder}", env="conanbuild")

    def package(self):
        with _prepend_environment(**self._package_paths()):
            Meson(self).install()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "spiel-1.0")
        self.cpp_info.libs = ["spiel-1.0"]
        self.cpp_info.includedirs = ["include/spiel"]
        self.cpp_info.requires = [
            "glib::gio-2.0", "libspeechprovider::libspeechprovider",
            "gstreamer::gstreamer", "gst-plugins-base::gst-plugins-base",
        ]
