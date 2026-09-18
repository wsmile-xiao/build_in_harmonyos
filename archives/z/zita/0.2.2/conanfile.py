#!/usr/bin/env python3
"""Conan recipe for zita 0.2.2 (upstream zita-rev1, Fons Adriaensen).

Pure-Makefile JACK reverb processor with an X11 GUI (source/Makefile, no
configure script, no upstream test target). Builds the executable
`zita-rev1` plus a set of PNG control graphics (share/zita-rev1/).

OHOS portability notes (see notes.md):
  - Upstream hardcodes `CXXFLAGS += -march=native`; removed so the Conan
    profile toolchain controls code generation.
  - OpenHarmony has no bare `install` on PATH; the Makefile now uses
    `INSTALL ?= /bin/install` (toybox).
  - clthreads.h guards `pthread_cancel` (absent in OHOS libc) behind
    `CLTHREADS_NO_PTHREAD_CANCEL`; build passes the macro.
  - X11 public headers (X11/Xos.h, ...) come from xorgproto, freetype2
    headers live under include/freetype2; dep include dirs are injected via
    CPPFLAGS so the Makefile's `pkgconf --cflags freetype2` probe is not
    needed (no pkgconf on OHOS PATH).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ZitaConan(ConanFile):
    name = "zita"
    version = "0.2.2"
    description = "zita-rev1 0.2.2: JACK reverb processor with X11 GUI (Fons Adriaensen)"
    license = "GPL-3.0-or-later"
    homepage = "https://kokkinizita.linuxaudio.org/linuxaudio/index.html"
    url = "https://kokkinizita.linuxaudio.org/linuxaudio/index.html"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("clthreads/2.4.0")
        self.requires("clxclient/3.9.2")
        self.requires("jack/1.9.22")
        self.requires("libpng/1.6.58")
        self.requires("cairo/1.18.4.1")
        self.requires("freetype/2.14.3")
        # --- version unification forced by the published OHOS recipes ---
        # clxclient/3.9.2 pins libxft/2.3.8; cairo's OHOS layer pins
        # libx11/libxext 6.4.0; the libxft chain pulls fontconfig 2.18.3.
        self.requires("libxft/2.3.8", override=True)
        self.requires("libx11/6.4.0", override=True)
        self.requires("libxext/6.4.0", override=True)
        self.requires("fontconfig/2.18.3", override=True)

    def layout(self):
        basic_layout(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("zita/0.2.2 supports Linux and OHOS only")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        # Inject every host dependency's include/lib dirs through the
        # build environment; the Makefile accumulates CPPFLAGS via `+=`.
        env = Environment()
        incs, libs = [], []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue  # build-requirements (e.g. util-macros) have none
            for inc in dep.cpp_info.includedirs or []:
                incs.append("-I" + os.path.join(dep.package_folder, inc))
            for libdir in dep.cpp_info.libdirs or []:
                libs.append("-L" + os.path.join(dep.package_folder, libdir))
        if incs:
            env.append("CPPFLAGS", " ".join(incs))
        if libs:
            env.append("LDFLAGS", " ".join(libs))
        env.append("CXXFLAGS", "-DCLTHREADS_NO_PTHREAD_CANCEL")
        env.vars(self).save_script("zita_deps_env")

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp") or "clang++"
        source_dir = os.path.join(self.source_folder, "source")
        # zita_deps_env carries CPPFLAGS/LDFLAGS/CXXFLAGS injected in
        # generate(); load it together with conanbuild (PassEnvironment
        # applies both scripts in the child process).
        self.run(
            f'make -C "{source_dir}" -j1 CXX="{cxx}" zita-rev1',
            env=["conanbuild", "zita_deps_env"],
        )

    def package(self):
        source_dir = os.path.join(self.source_folder, "source")
        # PREFIX=/ -> bin/zita-rev1 and share/zita-rev1/*.png under DESTDIR.
        self.run(
            f'make -C "{source_dir}" install DESTDIR="{self.package_folder}" '
            "PREFIX=/ INSTALL=/bin/install",
            env=["conanbuild", "zita_deps_env"],
        )

    def package_info(self):
        # Application package: no cpp_info.libs. The packaged artifact is
        # the zita-rev1 executable (declared via commands.json per R38).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []