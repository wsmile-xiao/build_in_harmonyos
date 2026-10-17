#!/usr/bin/env python3
"""Conan recipe — vonsh 1.1 (upstream plain Makefile, SDL2 game shell).

vonsh is an SDL2 "shell" game. The Makefile hardcodes system-wide SDL
paths via LDLIBS/CFLAGS with `=`/`?=`; both are overridden on the make
command line with the Conan-provided include/lib dirs. -lSDL2main is
dropped: the Conan sdl2 package does not ship the WinMain shim and the
game has a plain main(). Upstream ships no test suite, so a headless
smoke run (SDL dummy video/audio drivers) carries the verification.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class VonshConan(ConanFile):
    name = "vonsh"
    version = "1.1"
    description = "vonsh — a minimal SDL2 shell game"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/aurb/vonsh"
    url = ""  # CI fills this
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Vonsh Makefile: -lSDL2 -lSDL2main -lSDL2_image -lSDL2_mixer -lcjson -lm.
        # The ohpcd sdl2-image ships a static libSDL2_image.a whose WEBP/TIFF
        # loaders need libwebp/libtiff at link time, so both are declared.
        self.requires("sdl2/2.30.10")
        self.requires("sdl2-image/2.8.12")
        self.requires("sdl2-mixer/2.8.2")
        self.requires("cjson/1.7.19")
        self.requires("libwebp/1.6.0")
        self.requires("libtiff/4.7.2")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_flags(self):
        cflags = []
        ldlibs = ["-lm"]
        # Link order matters for static archives: image/mixer first, then the
        # webp/tiff archives their members reference, then SDL2, then cjson.
        dep_order = (
            "sdl2", "sdl2-image", "sdl2-mixer", "libwebp", "libtiff", "cjson",
        )
        for dep_name in dep_order:
            dep = self.dependencies[dep_name]
            pkg_inc = os.path.join(dep.package_folder, dep.cpp_info.includedirs[0])
            cflags.append(f"-I{pkg_inc}")
            # SDL headers are included both ways across the family:
            # <SDL.h>-style needs .../include/SDL2 on the path, while
            # <SDL2/SDL.h>-style needs its parent. Cover both.
            sdl2_sub = os.path.join(pkg_inc, "SDL2")
            if os.path.isdir(sdl2_sub):
                cflags.append(f"-I{sdl2_sub}")
            elif os.path.basename(pkg_inc) == "SDL2":
                cflags.append(f"-I{os.path.dirname(pkg_inc)}")
            pkg_lib = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
            ldlibs.append(f"-L{pkg_lib}")
            for lib in dep.cpp_info.libs:
                ldlibs.append(f"-l{lib}")
        return " ".join(cflags), " ".join(ldlibs)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        cflags, ldlibs = self._dep_flags()
        base = (
            "-std=c99 -D_DEFAULT_SOURCE -pedantic -O2 "
            "-D_FORTIFY_SOURCE=2 -fstack-protector-strong "
            f"-Iinc -DVERSION_STR=\\\"{self.version}\\\" {cflags}"
        )
        # CFLAGS uses `?=`/`+=` upstream — a command-line override replaces the
        # whole chain, so the upstream flag set is replicated here. LDLIBS
        # (`=`) is likewise overridden; -lSDL2main is dropped (see docstring).
        self.run(
            f"make -j2 CC={cc} STRIP=true VERSION_STR={self.version} "
            f"CFLAGS='{base}' LDLIBS='{ldlibs}' LDFLAGS='-Wl,-z,relro,-z,now'",
            cwd=self.source_folder,
        )

    def package(self):
        src = self.source_folder
        copy(self, "usr/games/vonsh", src=src,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        # RES_DIR is compiled as "../share/games/vonsh/" — the resources must
        # sit one level up from bin/ for the game to find its PNG/WAV assets.
        copy(self, "usr/share/games/vonsh/*", src=src,
             dst=os.path.join(self.package_folder, "share/games/vonsh"),
             keep_path=False)
        copy(self, "README.md", src=src,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
