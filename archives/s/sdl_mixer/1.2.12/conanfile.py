#!/usr/bin/env python3
"""SDL_mixer 1.2.12 Conan recipe for HarmonyOS PC."""

import os
import shlex
import stat

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rm,
    save,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SdlmixerConan(ConanFile):
    name = "sdl_mixer"
    version = "1.2.12"
    description = "Audio mixer library for SDL 1.2"
    license = "Zlib"
    homepage = "https://www.libsdl.org/projects/SDL_mixer/"
    url = "https://www.libsdl.org/projects/SDL_mixer/release/SDL_mixer-1.2.12.tar.gz"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl12-compat/1.2.68")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        AutotoolsDeps(self).generate()
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--disable-music-mod",
            "--disable-music-mod-modplug",
            "--disable-music-midi",
            "--disable-music-ogg",
            "--disable-music-flac",
            "--disable-music-mp3",
            "--disable-music-mp3-mad-gpl",
        ])
        if not self.options.shared:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.generate()

    def build(self):
        self._restore_helper_modes(
            self.source_folder,
            (
                "configure",
                "build-scripts/config.guess",
                "build-scripts/config.sub",
                "build-scripts/install-sh",
                "build-scripts/mkinstalldirs",
            ),
        )
        sdl_config = self._write_sdl_config()
        apply_conandata_patches(self)
        configure_args = [
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--disable-music-mod",
            "--disable-music-mod-modplug",
            "--disable-music-midi",
            "--disable-music-ogg",
            "--disable-music-flac",
            "--disable-music-mp3",
            "--disable-music-mp3-mad-gpl",
            "--enable-static",
            "--disable-shared",
        ]
        prefix = self._environment_prefix(sdl_config)
        self.run(
            f"{prefix} {shlex.join([os.path.join(self.source_folder, 'configure'), *configure_args])}",
            env="conanbuild",
        )
        self.run(f"{prefix} MAKEINFO=/bin/true make -j1", env="conanbuild")

    def _write_sdl_config(self):
        dependency = self.dependencies.host["sdl12-compat"]
        include_dir = os.path.join(dependency.package_folder, "include", "SDL")
        lib_dir = os.path.join(dependency.package_folder, "lib")
        path = os.path.join(self.build_folder, "sdl-config")
        save(
            self,
            path,
            f"""#!/bin/sh
case "$1" in
  --version) printf '%s\\n' '1.2.68' ;;
  --prefix|--exec-prefix) printf '%s\\n' '{dependency.package_folder}' ;;
  --cflags) printf '%s\\n' '-I{include_dir}' ;;
  --libs|--static-libs) printf '%s\\n' '-L{lib_dir} -lSDL-1.2' ;;
  *) exit 1 ;;
esac
""",
        )
        executable_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        os.chmod(path, os.stat(path).st_mode | executable_bits)
        return path

    def package(self):
        prefix = self._environment_prefix(os.path.join(self.build_folder, "sdl-config"))
        self.run(
            f"{prefix} MAKEINFO=/bin/true make -j1 install DESTDIR={shlex.quote(self.package_folder)}",
            env="conanbuild",
        )
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def _environment_prefix(self, sdl_config):
        lib_dirs = [
            os.path.join(dependency.package_folder, "lib")
            for dependency in self.dependencies.host.values()
        ]
        bin_dirs = [
            os.path.join(dependency.package_folder, "bin")
            for dependency in self.dependencies.host.values()
        ]
        assignments = [
            "CONFIG_SHELL=/bin/sh",
            "SHELL=/bin/sh",
            f"SDL_CONFIG={shlex.quote(sdl_config)}",
            f"PATH={shlex.quote(self.build_folder)}:{':'.join(bin_dirs)}:$PATH",
            f"LD_LIBRARY_PATH={':'.join(lib_dirs)}:$LD_LIBRARY_PATH",
        ]
        return " ".join(assignments)

    def package_info(self):
        self.cpp_info.libs = ["SDL_mixer"]
        self.cpp_info.requires = ["sdl12-compat::sdl12-compat"]
        self.cpp_info.set_property("cmake_file_name", "SDL_mixer")
        self.cpp_info.set_property("cmake_target_name", "SDL_mixer::SDL_mixer")

    @staticmethod
    def _restore_helper_modes(root, names):
        executable_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        for name in names:
            path = os.path.join(root, name)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | executable_bits)
