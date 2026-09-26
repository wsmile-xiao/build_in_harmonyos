#!/usr/bin/env python3
"""Conan recipe for jaaa 0.9.2 (Fons Adriaensen).

jaaa is an X11 audio analyser / level meter whose input comes from either
JACK (-J) or ALSA (-A).  Upstream is a pure-Makefile project: source/Makefile
plus five .cc and five .h files, no configure script, no autoconf, no CMake,
and no test or check target.

OHOS portability notes (see notes.md):
  - The compiler is referenced as the *variable* $(CXX) (source/Makefile line
    35 links with $(CXX); the .cc -> .o step goes through make's built-in
    implicit rule, which also expands $(CXX)).  So the recipe overrides CXX
    from the Conan profile instead of patching a compiler name literal.  This
    differs from sibling kokkinizita packages (aliki, jnoise) whose Makefiles
    hardcode "g++" in the rule's command position.
  - GNU Make on the build host predefines CXX to a dangling SDK path from the
    machine that built make, so an unqualified "make" fails with
    "No such file or directory" / Error 127 even though clang++ is installed.
  - The Makefile probes FreeType with pkgconf, which does not exist on
    OpenHarmony (only pkg-config does).  The patch swaps that line for a
    $(PCONFCFL) include slot and this recipe injects the dependency include
    and lib directories into it.
  - -march=native is dropped so the profile toolchain controls code generation.
  - OpenHarmony has no "install" on PATH (the toybox applet exists only as
    /bin/install and /bin is not on PATH), so the patch parameterises INSTALL.
  - The FFT dependency is single-precision FFTW: mainwin.cc calls fftwf_* and
    the Makefile links -lfftw3f, so the requirement is the fftw3f package, not
    fftw (every published fftw binary is configured with ENABLE_FLOAT=OFF and
    ships no libfftw3f).
  - PREFIX=/ is used for staging, so no host installation prefix is baked into
    the binary or written into the package layout.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class JaaaConan(ConanFile):
    name = "jaaa"
    version = "0.9.2"
    package_type = "application"
    description = "JACK and ALSA audio analyser and level meter (X11 GUI)"
    license = "GPL-2.0-or-later"
    homepage = "https://kokkinizita.linuxaudio.org/linuxaudio/"
    url = ""  # CI fills this

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("jaaa supports Linux and OHOS only")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("jaaa supports OHOS armv8 only")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # GUI toolkit (clxclient pulls Xft/X11/FreeType/fontconfig/Xrender and
        # pins clthreads/2.4.0 -- see notes.md for why clthreads is 2.4.0 and
        # not 2.4.2 here).
        self.requires("clxclient/3.9.2", transitive_headers=True)
        self.requires("clthreads/2.4.0", transitive_headers=True)
        self.requires("libxft/2.3.8", transitive_headers=True)
        self.requires("libx11/1.8.13", transitive_headers=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("fontconfig/2.18.3", transitive_headers=True)
        self.requires("libxrender/0.9.12", transitive_headers=True)
        self.requires("freetype/2.14.3", transitive_headers=True)
        # Audio back ends: jaaa links both -ljack and -lasound directly.
        self.requires("jack/1.9.22", transitive_headers=True)
        self.requires("zita-alsa-pcmi/0.6.1", transitive_headers=True)
        self.requires("alsa-lib/1.2.16", transitive_headers=True)
        # DSP: single-precision FFTW (fftwf_* API, -lfftw3f).
        self.requires("fftw3f/3.3.10", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        source_dir = os.path.join(self.source_folder, "source")
        # R33: the compiler must come from the Conan profile conf, never from
        # a bare shell ${CXX} (empty on CI/release workers).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        # Collect the include/lib search paths of every declared dependency
        # and hand them to the Makefile through its $(PCONFCFL) slot, so the
        # built-in -DVERSION/-DPREFIX definitions stay intact.
        pconfcfl = " -I."
        if str(self.settings.os) == "OHOS":
            # clthreads' package_info defines CLTHREADS_NO_PTHREAD_CANCEL for
            # OHOS consumers (pthread_cancel is absent on musl/OHOS); this
            # bare-make build does not consume it through CMakeDeps.
            pconfcfl += " -DCLTHREADS_NO_PTHREAD_CANCEL"
        ldflags = ""
        for _, dependency in self.dependencies.items():
            if not dependency.package_folder:
                continue
            for incdir in dependency.cpp_info.includedirs:
                path = incdir
                if not os.path.isabs(path):
                    path = os.path.join(dependency.package_folder, incdir)
                pconfcfl += " -I" + path
            for libdir in dependency.cpp_info.libdirs:
                path = libdir
                if not os.path.isabs(path):
                    path = os.path.join(dependency.package_folder, libdir)
                ldflags += " -L" + path
        # PREFIX=/ keeps the staged layout free of any host prefix and also
        # keeps -DPREFIX from baking "/usr/local" into the binary.
        self.run(
            'make -C "{}" -j1 PREFIX=/ CXX="{}" PCONFCFL="{}" LDFLAGS="{}" jaaa'.format(
                source_dir, cxx, pconfcfl, ldflags
            )
        )
        # Upstream ships no test/check target ("make check" fails with
        # "No rule to make target 'check'") so there is no test step here;
        # see test_package/ for the packaged consumer smoke test.

    def package(self):
        source_dir = os.path.join(self.source_folder, "source")
        # BINDIR derives from PREFIX, so PREFIX=/ + DESTDIR stages bin/jaaa.
        self.run(
            'make -C "{}" install PREFIX=/ DESTDIR="{}"'.format(
                source_dir, self.package_folder
            )
        )

    def package_info(self):
        # jaaa is a standalone GUI tool; it exports no libraries.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
