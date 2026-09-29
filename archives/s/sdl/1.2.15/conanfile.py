#!/usr/bin/env python3
"""Conan recipe for SDL 1.2.15 — Simple DirectMedia Layer (legacy 1.2 line).

HarmonyOS (aarch64) adaptation.  SDL 1.2.15 (2012) is the final upstream
release of the 1.2 line; it uses autotools with 2009-vintage helper scripts.

Three portability patches are required (see conandata.yml):

* ``0001-config-guess-ohos.patch`` / ``0002-config-sub-ohos.patch`` — the
  bundled config.guess/sub predate aarch64 and HarmonyOS entirely: without
  them ``configure`` cannot guess the build type, and ``config.sub`` rejects
  both ``aarch64`` and ``linux-ohos``.
* ``0003-configure-umask-022.patch`` — ``config.status`` creates its
  temporary directory with ``umask 077``; on the setgid hmdfs volume the
  on-disk owner is not the build UID, so a 0700 directory is unwritable even
  for its creator (``can't create ./confXXXXXX/out: Permission denied``).
  ``umask 022`` creates the same directory as 0755 and works.

Backends: this recipe builds a headless-capable SDL with the **dummy** video
driver (plus ALSA audio when the library is present).  X11/DirectFB/fbcon/
OpenGL and the exotic console backends are disabled — they need display
stacks the OHOS sandbox does not provide.  Consumers select the dummy driver
with ``SDL_VIDEODRIVER=dummy``; the compiled drivers are still discoverable
via ``SDL_VideoDriverName()``.

R26: ``libSDL-1.2`` is not a system library name on OHOS — no collision.
R32: settings.os must check in ("Linux", "OHOS").
R38: library package — no commands.json.
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Video/audio backends that need a display stack or platform audio daemon the
# OHOS sandbox does not provide.
_DISABLED_VIDEO = [
    "x11", "directfb", "fbcon", "ggi", "svga", "aalib", "caca", "photon",
    "carbon", "cocoa", "nanox", "qtopia", "picogui", "ps2gs", "ps3", "vgl",
    "wscons", "xbios", "gem", "opengl",
]
_DISABLED_AUDIO = ["esd", "nas", "arts", "pulseaudio", "diskaudio", "oss"]
_DISABLED_MISC = ["input-tslib", "screensaver", "assembly", "nasm", "altivec"]


class SdlConan(ConanFile):
    name = "sdl"
    version = "1.2.15"
    description = "Simple DirectMedia Layer (legacy 1.2 line) — cross-platform multimedia library"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.libsdl.org/"
    url = "https://github.com/libsdl-org/SDL-1.2"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False], "alsa": [True, False]}
    default_options = {"shared": False, "fPIC": True, "alsa": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # SDL 1.2 is a C library.
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)
        # SDL 1.2 must be configured/built in-source: the tarball ships a
        # top-level Makefile.in and configure writes Makefile + the config
        # headers into the source tree (no VPATH support).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps gives us a uniform way to point configure at the
        # Conan-provided libs via --with-... overrides below.
        pass

    def _configure_args(self):
        args = [
            "--host=aarch64-unknown-linux-ohos",
            # configure's conftest linking is unreliable in the sandbox;
            # pre-seed both answers (ac_cv_prog_cc_works is checked first by
            # AC_PROG_CC, ac_cv_prog_cc_cross by the cross branch).
            "ac_cv_prog_cc_works=yes",
            "ac_cv_prog_cc_cross=yes",
            "--disable-shared" if not self.options.shared else "--enable-shared",
            "--enable-static" if not self.options.shared else "--disable-static",
            "--disable-libtool-lock",
        ]
        for backend in _DISABLED_VIDEO:
            args.append("--disable-video-%s" % backend)
        for backend in _DISABLED_AUDIO:
            args.append("--disable-%s" % backend)
        for item in _DISABLED_MISC:
            args.append("--disable-%s" % item)
        args.append("--enable-video-dummy")
        args.append("--enable-dummyaudio")
        args.append("--enable-alsa" if self.options.alsa else "--disable-alsa")
        args.append("--enable-alsa-shared")
        args.append("--disable-alsatest")
        return args

    def build(self):
        apply_conandata_patches(self)

        # The 2009 tree lacks a generated `depend` target prerequisite in a
        # few subdirs; `make` still builds the libraries.  Use the hnp
        # toolchain explicitly (R33: no reliance on shell env).
        cc = os.environ.get("CC", "/data/service/hnp/bin/clang")
        cxx = os.environ.get("CXX", "/data/service/hnp/bin/clang++")

        configure = os.path.join(self.source_folder, "configure")
        # Capability macro (R8: no platform macros in patches): musl does not
        # implement POSIX thread cancellation, so the pthread-cancel guard in
        # patch 0004 is driven from here instead of a __OHOS__ branch.
        cmd = ["sh", configure, "CC=%s" % cc, "CXX=%s" % cxx,
               "CPPFLAGS=-DSDL_NO_THREAD_CANCEL"] + self._configure_args()
        self.run(" ".join('"%s"' % a if " " in a else a for a in cmd),
                 cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # `make install` is not used: install-sh carries the hmdfs ownership
        # quirks and would also install the (disabled-backend) headers twice.
        libs = []
        for pattern in ("build/.libs/libSDL*.a", "build/.libs/libSDL*.so*"):
            libs.extend(glob.glob(os.path.join(self.source_folder, pattern)))
        if not libs:
            # SDL 1.2 builds in-source: libs land in build/.libs or .libs
            for pattern in (".libs/libSDL*.a", ".libs/libSDL*.so*"):
                libs.extend(glob.glob(os.path.join(self.source_folder, pattern)))
        if not libs:
            raise ConanException("no SDL library produced")
        for lib in libs:
            copy(self, os.path.basename(lib), src=os.path.dirname(lib),
                 dst=os.path.join(self.package_folder, "lib"))
        # keep_path=False: the glob carries the "include/" prefix, which would
        # otherwise be preserved and land the headers at
        # include/SDL/include/SDL.h instead of the traditional include/SDL/.
        copy(self, "include/*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include", "SDL"),
             keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SDL")
        self.cpp_info.set_property("pkg_config_name", "sdl")
        self.cpp_info.libs = ["SDL"]
        self.cpp_info.includedirs = ["include", "include/SDL"]
        if not self.options.shared:
            self.cpp_info.defines = ["SDL_STATIC"]
        if str(self.settings.os) == "Linux":
            self.cpp_info.system_libs = ["m", "dl", "pthread"]

    def requirements(self):
        if self.options.alsa:
            self.requires("alsa-lib/1.2.16")
