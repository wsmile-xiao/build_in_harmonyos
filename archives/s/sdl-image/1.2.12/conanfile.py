#!/usr/bin/env python3
"""SDL_image 1.2.12 - HarmonyOS PC (aarch64) Conan recipe.

Adaptation notes
================
* SDL 1.2 is supplied by sdl12-compat/1.2.68, which re-implements the SDL 1.2
  ABI on top of SDL2 (the original SDL 1.2 tree does not build on OHOS).
* SDL discovery: acinclude/sdl.m4 asks pkg-config for the module "sdl" and
  only afterwards falls back to a `sdl-config` script.  Both paths are dead
  ends here:
    - the sdl12-compat package ships lib/pkgconfig/sdl12_compat.pc, so the
      pkg-config module name "sdl" never resolves;
    - the sdl-config shipped in that package has the *package builder's*
      absolute prefix baked in, so it points nowhere on any other machine.
  SDL_CFLAGS / SDL_LIBS are therefore handed to configure explicitly.  They
  are AC_ARG_VAR "precious" variables documented as "overriding pkg-config"
  (configure:1547), and PKG_CHECK_MODULES reports sdl_pc=yes as soon as they
  are already set, so neither probe is consulted.
* The --enable-*-shared format switches mean "dlopen the codec at runtime".
  They are disabled so the codecs become ordinary link-time dependencies and
  the Conan dependency chain (self.requires) stays authoritative.
* patches/0001-config.sub.patch teaches the vendored 2012 config.sub about
  aarch64 and -ohos; config.guess stays pristine to keep the patch minimal.
  The dual triplet is additionally passed explicitly, which pins autoconf
  into cross mode and keeps its conftest scratch directories (created with
  `mktemp -d`, mode 0700) out of the picture on platforms where those are
  not writable.
* Upstream ships no test suite at all (only the noinst_PROGRAMS "showimage"
  demo), hence the two independent consumer tests in test_package/ provide
  package-level and HarmonyOS-specific validation.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class SdlImageConan(ConanFile):
    name = "sdl-image"
    version = "1.2.12"
    description = (
        "SDL_image 1.2 - image loading library for SDL 1.2 "
        "(BMP/GIF/JPEG/LBM/PCX/PNG/PNM/TGA/TIFF/WEBP/XCF/XPM/XV)"
    )
    license = "Zlib"
    homepage = "https://www.libsdl.org/projects/SDL_image/"
    topics = ("sdl", "sdl1.2", "sdl12-compat", "image", "png", "jpeg", "webp", "tiff", "ohos")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # sdl12-compat provides the SDL 1.2 API (SDL.h / libSDL-1.2.so)
        self.requires("sdl12-compat/1.2.68")
        # codecs loaded through the external libraries rather than dlopen()
        # (libpng/1.6.58 is the revision that shares zlib/1.3.1.1 with
        # libtiff/4.7.2, so the whole codec set resolves without a zlib clash)
        self.requires("libpng/1.6.58")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libtiff/4.7.2")
        self.requires("libwebp/1.6.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        sdl_prefix = self.dependencies["sdl12-compat"].package_folder
        sdl_libdir = os.path.join(sdl_prefix, "lib")
        # sdl12-compat publishes the compatibility library under both the
        # drop-in SDL 1.2 name and the plain SDL name; use whichever is
        # actually present in the package that got resolved.
        if any(
            os.path.exists(os.path.join(sdl_libdir, name))
            for name in ("libSDL-1.2.so", "libSDL-1.2.a")
        ):
            sdl_lib = "-lSDL-1.2"
        else:
            sdl_lib = "-lSDL"

        # SDL.h itself lives in include/SDL, and it includes "begin_code.h"
        # from the same directory, so both spellings are put on the path.
        sdl_cflags = "-I{} -I{}".format(
            os.path.join(sdl_prefix, "include", "SDL"),
            os.path.join(sdl_prefix, "include"),
        )
        sdl_libs = "-L{} -Wl,-rpath-link,{} {}".format(sdl_libdir, sdl_libdir, sdl_lib)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--enable-shared" if self.options.shared else "--disable-shared",
                "--disable-static" if self.options.shared else "--enable-static",
                # link the codecs instead of dlopen()-ing them at run time
                "--disable-png-shared",
                "--disable-jpg-shared",
                "--disable-tif-shared",
                "--disable-webp-shared",
                # AC_ARG_VAR overrides: there is no usable "sdl" pkg-config
                # module nor a correct sdl-config in the dependency package
                "SDL_CFLAGS=" + sdl_cflags,
                "SDL_LIBS=" + sdl_libs,
                # the worker sandbox cannot execute a freshly linked conftest
            ]
        )
        if self.settings.os == "OHOS":
            # AutotoolsToolchain injects no OHOS triplet here and the vendored
            # 2012 config.guess cannot identify the HarmonyOS build host, so
            # state both triplets explicitly.  The differing build triplet puts
            # autoconf into cross-compiling mode, which skips its "can the
            # compiler output be run" probe (it cannot here: unsigned ELF).
            tc.configure_args.extend(
                [
                    "--build=x86_64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        Autotools(self).install()
        # libtool archives hold absolute build paths and must not leak out
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["SDL_image"]
        self.cpp_info.set_property("cmake_file_name", "SDL_image")
        self.cpp_info.set_property("cmake_target_name", "SDL_image::SDL_image")
        self.cpp_info.set_property("pkg_config_name", "SDL_image")
