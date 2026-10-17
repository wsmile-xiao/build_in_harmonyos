#!/usr/bin/env python3
"""Conan recipe for clxclient 3.9.0 (Fons Adriaensen).

Pure-Makefile shared library (top-level Makefile, flat layout) that wraps
the Xlib/Xft toolkit with a C++ class hierarchy. No configure script, no
upstream test target. Builds libclxclient.so.3.9.0 against the published
libx11, libxft, freetype and clthreads packages.

OHOS portability notes (see notes.md):
  - The upstream Makefile probes freetype via `freetype-config --cflags`
    and hardcodes /usr/X11R6 include/lib paths; the portability patch
    removes both so include/lib paths come from the Conan dependencies.
  - The link rule hardcodes `g++`; the patch switches it to $(CXX) so the
    toolchain from the Conan profile (tools.build:compiler_executables)
    controls code generation.
  - OpenHarmony has no bare `install`/`ldconfig` on PATH, and the HMBS
    install shim must not sit on the staging path; the patch stages with
    absolute `/bin/mkdir -p`/`/bin/cp -f` (plus `/bin/ln -sf` for the
    symlink chain) and drops ldconfig, so no PATH-resolved coreutils
    (e.g. a broken harmonybrew `rm`) is executed.
  - The install target gains DESTDIR staging support and emits the full
    symlink chain (libclxclient.so -> .so.3 -> .so.3.9.0) so the runtime
    loader can resolve the SONAME and consumers can link with -lclxclient.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ClxclientConan(ConanFile):
    name = "clxclient"
    version = "3.9.0"
    package_type = "library"
    description = "C++ wrapper library for the X11 protocol"
    license = "LGPL-2.1-or-later"
    homepage = "https://kokkinizita.linuxaudio.org/linuxaudio/"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("clxclient supports Linux and OHOS only")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("clxclient supports OHOS armv8 only")
        if not self.options.shared:
            raise ConanInvalidConfiguration("clxclient 3.9.0 only builds a shared library")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libx11/1.8.13", transitive_headers=True)
        self.requires("libxft/2.3.8", transitive_headers=True)
        self.requires("freetype/2.14.3", transitive_headers=True)
        self.requires("clthreads/2.4.0", transitive_headers=True)
        # clxclient.h includes <X11/Xos.h>, which is shipped by xorgproto
        # (libx11's own package_info does not re-export the xorgproto include
        # directory), so the X11 compat headers must be inherited explicitly.
        self.requires("xorgproto/2025.1", transitive_headers=True)
        # Xft.h includes <fontconfig/fontconfig.h>; libxft's package_info
        # re-exports fontconfig but the compiler needs the include directory
        # injected at build time, so declare it here as well.
        self.requires("fontconfig/2.18.3", transitive_headers=True)
        # Xft.h also includes <X11/extensions/Xrender.h>; the compiler needs
        # libxrender's include directory injected at build time.
        self.requires("libxrender/0.9.12", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _make_bin(self):
        make_bin = os.environ.get("HMBS_MAKE") or shutil.which("make") or "make"
        parts = os.environ.get("PATH", "").split(os.pathsep)
        filtered = [entry for entry in parts if "harmonybrew" not in entry]
        if filtered != parts:
            os.environ["PATH"] = os.pathsep.join(filtered)
        return make_bin

    def build(self):
        apply_conandata_patches(self)
        make_bin = self._make_bin()
        # 3.9.0 tarball uses a flat layout: Makefile lives at the archive
        # root (no source/ subdirectory, unlike 3.9.2).
        source_dir = self.source_folder
        # R33: compiler must come from the Conan profile conf, never a bare
        # shell ${CXX} (empty on CI/release workers).
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        x11 = self.dependencies["libx11"]
        xft = self.dependencies["libxft"]
        freetype = self.dependencies["freetype"]
        clthreads = self.dependencies["clthreads"]
        xorgproto = self.dependencies["xorgproto"]
        fontconfig = self.dependencies["fontconfig"]
        xrender = self.dependencies["libxrender"]
        # Inject include dirs / defines through the Makefile's `$(PCONFCFL)`
        # slot (appended to CPPFLAGS) instead of overriding CPPFLAGS, so the
        # Makefile's own `-DVERSION=\"$(VERSION)\"` definition is preserved.
        pconfcfl = ""
        # enumip.cc uses `#include <clxclient.h>` (angled); the include lives
        # in the same directory, so expose the source dir as -I. .
        pconfcfl += " -I."
        if str(self.settings.os) == "OHOS":
            # clthreads' package_info defines CLTHREADS_NO_PTHREAD_CANCEL for
            # OHOS consumers (pthread_cancel is absent); our make build does
            # not consume that define through CMakeDeps, so add it manually.
            pconfcfl += " -DCLTHREADS_NO_PTHREAD_CANCEL"
        pconfcfl += " -I" + os.path.join(x11.package_folder, "include")
        pconfcfl += " -I" + os.path.join(xft.package_folder, "include")
        # freetype 头在 include/freetype2/（ft2build.h + freetype/*.h）
        pconfcfl += " -I" + os.path.join(freetype.package_folder, "include/freetype2")
        pconfcfl += " -I" + os.path.join(clthreads.package_folder, "include")
        # <X11/Xos.h> 等兼容头由 xorgproto 提供
        pconfcfl += " -I" + os.path.join(xorgproto.package_folder, "include")
        # Xft.h 引用 <fontconfig/fontconfig.h>
        pconfcfl += " -I" + os.path.join(fontconfig.package_folder, "include")
        # Xft.h 引用 <X11/extensions/Xrender.h>
        pconfcfl += " -I" + os.path.join(xrender.package_folder, "include")
        ldflags = ""
        for dep in (x11, xft, freetype, clthreads, xorgproto, fontconfig, xrender):
            ldflags += " -L" + os.path.join(dep.package_folder, "lib")
        self.run(
            '{} -C "{}" -j1 CXX="{}" PCONFCFL="{}" LDFLAGS="{}" RM=/bin/rm '
            "libclxclient.so.3.9.0".format(make_bin, source_dir, cxx, pconfcfl, ldflags)
        )
        # Upstream ships no test/check target (`make check` fails with
        # "No rule to make target 'check'"); the recipe therefore has no
        # test step here. See test_package/ for the consumer-side test.

    def package(self):
        source_dir = self.source_folder
        make_bin = self._make_bin()
        # LIBDIR=lib fixes the Makefile's $(SUFFIX)-derived lib path.
        self.run(
            '{} -C "{}" install PREFIX=/ LIBDIR=lib DESTDIR="{}" RM=/bin/rm'.format(
                make_bin, source_dir, self.package_folder
            )
        )

    def package_info(self):
        self.cpp_info.libs = ["clxclient"]
        # The packaged .so links libXft.so/libX11.so (NEEDED) and its public
        # header includes <X11/Xft/Xft.h>, <X11/Xlib.h>, <clthreads.h> and
        # FreeType headers; consumers must inherit those include dirs and
        # link interfaces.
        self.cpp_info.requires = [
            "libx11::libx11",
            "libxft::libxft",
            "freetype::freetype",
            "clthreads::clthreads",
            "xorgproto::xorgproto",
            "fontconfig::fontconfig",
            "libxrender::libxrender",
        ]
        self.cpp_info.set_property("cmake_file_name", "clxclient")
        self.cpp_info.set_property("cmake_target_name", "clxclient::clxclient")
