#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Sdl2Ttf, sdl2-ttf, 2.24.0, sdl2-ttf 2.24.0, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class Sdl2TtfConan(ConanFile):
    name = "sdl2-ttf"
    version = "2.24.0"
    description = "sdl2-ttf 2.24.0"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10")
        self.requires("freetype/2.14.3")
        self.requires("harfbuzz/14.2.0.1.1.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Release tarball does not ship the external/ submodules; force use of
        # the system FreeType/HarfBuzz provided via conan requires.
        tc.configure_args.append("--disable-freetype-builtin")
        tc.configure_args.append("--disable-harfbuzz-builtin")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        tc.generate()
        # Inject dependency compile/link env (CPPFLAGS/LDFLAGS/PKG_CONFIG_PATH)
        # so configure can find SDL2, FreeType, HarfBuzz via pkg-config
        AutotoolsDeps(self).generate()
        # OHOS loader has no default search path for conan-cached shared libs
        # (freetype/harfbuzz are shared-only). configure's conftest runs compiled
        # programs, which fails with "Error loading shared library ...so.0"
        # unless LD_LIBRARY_PATH points at the dependency lib dirs.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
                env.prepend_path("PKG_CONFIG_PATH", os.path.join(libdir, "pkgconfig"))
            for bindir in dep.cpp_info.bindirs:
                env.prepend_path("PATH", bindir)
        # sdl2.pc inside the conan package resolves prefix to empty, so
        # pkg-config yields -I//include/SDL2 which does not exist. Inject the
        # real SDL2 header dir so #include "SDL.h" resolves (same as sdl2_image).
        sdl2 = self.dependencies.get("sdl2")
        if sdl2 and sdl2.package_folder:
            env.append("CPPFLAGS", "-I" + os.path.join(sdl2.package_folder, "include", "SDL2"))
        # harfbuzz.pc Requires.private references glib-2.0.pc which is not
        # installed in the conan cache, so the pkg-config check fails. configure
        # honors preset HB_CFLAGS/HB_LIBS, bypassing pkg-config for HarfBuzz.
        hb = self.dependencies.get("harfbuzz")
        if hb and hb.package_folder:
            hb_inc = os.path.join(hb.package_folder, "include")
            hb_lib = os.path.join(hb.package_folder, "lib")
            env.define("HB_CFLAGS", "-I{}/harfbuzz -I{}".format(hb_inc, hb_inc))
            env.define("HB_LIBS", "-L{} -lharfbuzz".format(hb_lib))
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["SDL2_ttf"]
        # Static lib transitively needs SDL2, FreeType, HarfBuzz
        self.cpp_info.requires = ["sdl2::sdl2", "freetype::freetype", "harfbuzz::harfbuzz"]
        # Upstream installs headers into include/SDL2/; SDL_ttf.h does
        # #include "SDL.h", so consumers need include/SDL2 on the path
        self.cpp_info.includedirs = ["include/SDL2", "include"]
        # SDL_ttf.h includes "SDL.h"; sdl2 package only exposes include/,
        # so expose sdl2's include/SDL2 dir here (same as sdl2_image)
        sdl2 = self.dependencies.get("sdl2")
        if sdl2 and sdl2.package_folder:
            self.cpp_info.includedirs.append(os.path.join(sdl2.package_folder, "include", "SDL2"))
