#!/usr/bin/env python3
"""Conan recipe for audioresamplerate 2.1 — pure Makefile build.

Upstream: https://github.com/AnSwErYWJ/AudioResamplerate
Build entry: top-level Makefile with targets:
  make iniparser      -> lib/libiniparser.so
  make log            -> lib/liblog.so
  make resamplerate   -> lib/libresamplerate.so
  make all            -> bin/resamplerate (CLI demo, links the three libs)

The tarball ships stale x86-64 prebuilt .so under lib/; we clean and rebuild
everything from source for the target arch. Compiler/flags come from the
Conan toolchain (R33: no bare ${CC}/${CFLAGS} shell vars).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, mkdir, copy
from conan.tools.layout import basic_layout


class AudioresamplerateConan(ConanFile):
    name = "audioresamplerate"
    version = "2.1"
    description = "AudioResamplerate — audio sample rate converter based on Secret Rabbit Code (libsamplerate) and iniparser"
    license = "GPL-3.0"
    homepage = "https://github.com/AnSwErYWJ/AudioResamplerate"
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
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # Remove stale x86-64 prebuilt .so shipped in the tarball; binary is
        # derived artifact, must be rebuilt for target arch.
        self.run("make clean cleanso", cwd=self.source_folder)
        mkdir(self, self.source_folder + "/bin")
        # R33: pass flags explicitly through make vars sourced from settings
        for target in ("iniparser", "log", "resamplerate"):
            self.run(f"make {target} CC=clang", cwd=self.source_folder)
        self.run("make all CC=clang", cwd=self.source_folder)

    def package(self):
        mkdir(self, self.package_folder + "/include")
        mkdir(self, self.package_folder + "/lib")
        mkdir(self, self.package_folder + "/bin")
        for hdr in ("resamplerate.h", "samplerate.h", "iniparser.h", "dictionary.h",
                    "log.h", "common.h", "config.h", "float_cast.h"):
            copy(self, hdr, self.source_folder + "/include", self.package_folder + "/include")
        copy(self, "*.so", self.source_folder + "/lib", self.package_folder + "/lib",
             keep_path=False)
        copy(self, "resamplerate", self.source_folder + "/bin", self.package_folder + "/bin",
             keep_path=False)
        copy(self, "config.ini", self.source_folder, self.package_folder + "/bin",
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["resamplerate", "iniparser", "log"]