#!/usr/bin/env python3
"""Conan recipe for the SDL_mixer 1.2.12 Autotools library on HarmonyOS."""

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm, rmdir
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class SdlMixerConan(ConanFile):
    name = "sdl-mixer"
    version = "1.2.12"
    description = "SDL 1.2 audio mixer library"
    homepage = "https://www.libsdl.org/projects/SDL_mixer/"
    license = "Zlib"
    topics = ("sdl", "audio", "mixer")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("sdl12-compat/1.2.68")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        sdl = self.dependencies["sdl12-compat"]
        sdl_include = os.path.join(sdl.package_folder, "include", "SDL")
        sdl_lib = os.path.join(sdl.package_folder, "lib")
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend([
            "--disable-shared" if not self.options.shared else "--enable-shared",
            "--enable-static" if not self.options.shared else "--disable-static",
            "--disable-music-mod",
            "--disable-music-ogg",
            "--disable-music-flac",
            "--disable-music-mp3",
            "--disable-music-midi",
            "--disable-music-cmd",
            "SDL_CFLAGS=-I{}".format(sdl_include),
            "SDL_LIBS=-L{} -Wl,-rpath-link,{} -lSDL-1.2".format(sdl_lib, sdl_lib),
        ])
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.configure_args.extend([
                "--build=x86_64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        toolchain.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        Autotools(self).install()
        copy(self, "SDL_mixer.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include", "SDL"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["SDL_mixer"]
        self.cpp_info.includedirs = [os.path.join("include", "SDL")]
        self.cpp_info.set_property("cmake_file_name", "SDL_mixer")
        self.cpp_info.set_property("cmake_target_name", "SDL_mixer::SDL_mixer")
        self.cpp_info.requires = ["sdl12-compat::sdl12-compat"]
