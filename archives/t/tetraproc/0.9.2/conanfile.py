#!/usr/bin/env python3
"""Conan recipe for tetraproc 0.9.2 (Fons Adriaensen).

Tetrahedral Microphone Processor for Ambisonic recording.  Ships two
programs built from one plain-Makefile source tree (source/Makefile):

  - tetraproc : X11/JACK GUI processor (needs a display + jackd at runtime)
  - tetrafile : command-line B-format file converter (pure CLI, testable)

No configure script, no upstream test target.  Builds against the
published clthreads, clxclient, fftw3f, jack, libsndfile, libpng, libx11,
libxft, freetype, fontconfig, libxrender and xorgproto packages.

OHOS portability notes (see notes.md and patches/0001):
  - The upstream Makefile hardcodes `CXXFLAGS += -march=native`; the patch
    removes it so the toolchain from the Conan profile
    (tools.build:compiler_executables) controls code generation.
  - The Makefile calls `pkg-config --cflags freetype2` to locate FreeType
    headers; on OHOS the freetype include directory comes from the freetype
    Conan package, so the pkg-config call is replaced by a FREETYPE_CFLAGS
    make variable supplied by the recipe.
  - Upstream links `-lrt`; OpenHarmony (musl) puts the clock/timer functions
    in libc and ships no librt, so -lrt is moved behind a SYSLIBS make
    variable (empty on OHOS, `-lrt` on Linux).
  - Extra -I / -L flags are injected through new PCONFCFL / CONAN_LDLIBS
    make slots so the Makefile's own -DVERSION / -DSHARED additions and
    target-specific LDLIBS appends are preserved.

Single-precision FFTW: this repository's "fftw" packages are built with
ENABLE_FLOAT=OFF and only ship the double-precision library (libfftw3).
tetraproc uses the single-precision fftwf_* API and links -lfftw3f, which
is provided by the dedicated fftw3f package (fftw3f/3.3.10) published by
the same artifact repository.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class TetraprocConan(ConanFile):
    name = "tetraproc"
    version = "0.9.2"
    package_type = "application"
    description = (
        "Tetrahedral Microphone Processor for Ambisonic recording "
        "(tetraproc X11/JACK GUI + tetrafile B-format converter CLI)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://kokkinizita.linuxaudio.org/linuxaudio/"
    url = ""  # CI fills this

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tetraproc supports Linux and OHOS only"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "tetraproc supports OHOS armv8 only"
            )

    def requirements(self):
        # X11 toolkit stack (same pins the clxclient/3.9.2 recipe proves)
        self.requires("libx11/1.8.13", transitive_headers=True)
        self.requires("libxft/2.3.8", transitive_headers=True)
        self.requires("freetype/2.14.3", transitive_headers=True)
        self.requires("fontconfig/2.18.3", transitive_headers=True)
        self.requires("libxrender/0.9.12", transitive_headers=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        # audio stack
        # clthreads/2.4.0: must match clxclient/3.9.2's own pin — a
        # different version here makes the graph conflict
        # (clthreads/2.4.0 vs 2.4.2 originates from clxclient).
        self.requires("clthreads/2.4.0", transitive_headers=True)
        self.requires("clxclient/3.9.2", transitive_headers=True)
        # single-precision FFTW (libfftw3f / libfftw3f_threads) — the
        # dedicated fftw3f package; the "fftw" packages here are
        # double-precision only
        self.requires("fftw3f/3.3.10", transitive_headers=True)
        self.requires("jack/1.9.22", transitive_headers=True)
        self.requires("libsndfile/1.2.2", transitive_headers=True)
        # png2img.cc includes <png.h>
        self.requires("libpng/1.6.58.3", transitive_headers=True)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["tetraproc"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        source_dir = os.path.join(self.source_folder, "source")

        # R33: compiler must come from the Conan profile conf, never a bare
        # shell ${CXX} (empty on CI/release workers).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"

        deps = {
            "libx11": "libx11", "libxft": "libxft", "freetype": "freetype",
            "fontconfig": "fontconfig", "libxrender": "libxrender",
            "xorgproto": "xorgproto", "clthreads": "clthreads",
            "clxclient": "clxclient", "fftw3f": "fftw3f", "jack": "jack",
            "libsndfile": "libsndfile", "libpng": "libpng",
        }
        dep = {k: self.dependencies[v] for k, v in deps.items()}

        pconfcfl = " -I."
        if str(self.settings.os) == "OHOS":
            # clthreads.h references pthread_cancel (sepuku); OHOS musl has
            # no pthread_cancel — clthreads' package_info defines
            # CLTHREADS_NO_PTHREAD_CANCEL for OHOS consumers, but this make
            # build does not consume that define through CMakeDeps, so add
            # it manually (same as the clxclient recipe).
            pconfcfl += " -DCLTHREADS_NO_PTHREAD_CANCEL"
        # png2img.cc includes <png.h> directly
        pconfcfl += " -I" + os.path.join(dep["libpng"].package_folder, "include")
        # audio headers
        pconfcfl += " -I" + os.path.join(dep["fftw3f"].package_folder, "include")
        pconfcfl += " -I" + os.path.join(dep["jack"].package_folder, "include")
        pconfcfl += " -I" + os.path.join(dep["libsndfile"].package_folder, "include")
        # Fons Adriaensen support libraries
        pconfcfl += " -I" + os.path.join(dep["clthreads"].package_folder, "include")
        pconfcfl += " -I" + os.path.join(dep["clxclient"].package_folder, "include")
        # X11 stack: Xft.h pulls fontconfig + Xrender; clxclient.h pulls X11
        # compat headers from xorgproto (see clxclient recipe rationale)
        pconfcfl += " -I" + os.path.join(dep["libx11"].package_folder, "include")
        pconfcfl += " -I" + os.path.join(dep["libxft"].package_folder, "include")
        pconfcfl += " -I" + os.path.join(
            dep["freetype"].package_folder, "include/freetype2"
        )
        pconfcfl += " -I" + os.path.join(dep["fontconfig"].package_folder, "include")
        pconfcfl += " -I" + os.path.join(dep["libxrender"].package_folder, "include")
        pconfcfl += " -I" + os.path.join(dep["xorgproto"].package_folder, "include")

        ldlibs = ""
        for d in dep.values():
            ldlibs += " -L" + os.path.join(d.package_folder, "lib")

        # OHOS (musl) has no librt; keep -lrt only on plain Linux
        syslibs = "" if str(self.settings.os) == "OHOS" else "-lrt"
        freetype_cflags = " -I" + os.path.join(
            dep["freetype"].package_folder, "include/freetype2"
        )

        self.run(
            'make -C "{}" -j1 CXX="{}" PCONFCFL="{}" FREETYPE_CFLAGS="{}" '
            'SYSLIBS="{}" CONAN_LDLIBS="{}"'.format(
                source_dir, cxx, pconfcfl, freetype_cflags, syslibs, ldlibs
            )
        )
        # Upstream ships no test/check target; consumer verification lives
        # in test_package/ (tetrafile --help smoke test).

    def package(self):
        source_dir = os.path.join(self.source_folder, "source")
        bindir = os.path.join(self.package_folder, "bin")
        sharedir = os.path.join(self.package_folder, "share", "tetraproc")
        copy(self, "tetraproc", src=source_dir, dst=bindir)
        copy(self, "tetrafile", src=source_dir, dst=bindir)
        copy(
            self, "*.png",
            src=os.path.join(self.source_folder, "share"), dst=sharedir,
        )
        copy(
            self, "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._sign_ohos_binaries(bindir)

    def _sign_ohos_binaries(self, bindir):
        # HarmonyOS XPM requires executed ELF files to be content-signed
        # (see fftw recipe rationale); only real files, never symlinks.
        if str(self.settings.os) != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for path in sorted(glob.glob(os.path.join(bindir, "*"))):
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            with open(path, "rb") as handle:
                if handle.read(4) != b"\x7fELF":
                    continue
            self.run(
                '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'
                .format(oc=objcopy, f=path)
            )
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
                .format(sg=signer, f=path)
            )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share/tetraproc"]
