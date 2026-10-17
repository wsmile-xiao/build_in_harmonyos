#!/usr/bin/env python3
"""Conan recipe for kew 4.2.5 (upstream bare Makefile build).

kew is a terminal music player written in C (plus one C++ TagLib wrapper).
The upstream build system is a single hand-written Makefile: no configure,
no CMake, no Meson.  All dependency flags come from pkg-config, which the
Makefile invokes through ``$(shell $(PKG_CONFIG) --cflags/--libs ...)``.

HarmonyOS PC adaptation points
------------------------------
* The Makefile resolves dependencies with pkg-config at *parse* time, so the
  Conan-generated ``.pc`` files (PkgConfigDeps) plus the packaged ``pkgconf``
  are injected through ``PKG_CONFIG_PATH`` / PATH of the ``conanbuild`` env.
* ``CC``/``CXX`` must be passed on the make command line: the Makefile forces
  ``CC := gcc`` whenever ``$(origin CC)`` is ``default`` (i.e. Conan did not put
  CC in the environment), and ``gcc``/``g++`` do not exist on the OHOS worker.
* ``UNAME_S=Linux`` is passed explicitly.  ``uname -s`` on HarmonyOS PC returns
  ``HarmonyOS``, so upstream's ``ifeq ($(UNAME_S),Linux)`` hardening block
  (``-fPIE``/``-pie``/``-Wl,-z,relro``/``-Wl,-z,now``) would be silently
  skipped.  The target really is an ELF/musl aarch64 system, so selecting that
  branch is the semantically correct choice and keeps the PIE/RELRO posture
  the platform's binary hardening gate expects.  ``-fcf-protection`` stays out
  of the way because it is guarded by ``$(ARCH)`` being x86_64/i386.
* ``USE_FAAD=0`` is passed explicitly.  faad2 autodetection probes hardcoded
  host prefixes (``/usr/lib``, ``/usr/local/lib``, Homebrew, Termux); the
  ``/usr/local/lib -lfaad`` fallback of that probe is not a valid assumption on
  OHOS, and no ``faad2`` conan package is published.  FAAD2/M4A support is an
  optional upstream feature (``make USE_FAAD=0``), so it is turned off instead
  of being emulated.  MP4/AAC metadata keeps working through TagLib.
* ``-lstdc++`` is kept (verified present in the OHOS toolchain) but the whole
  ``LIBS`` string is rebuilt so that the ``-L`` directories coming from
  pkg-config precede the literal ``-lopusfile -lglib-2.0`` entries; upstream
  puts ``$(LIBS)`` before ``$(LDFLAGS)``, so without that the Conan library
  directories would only be seen after the first ``-l``.
* GLib's gettext macros land on ``g_libintl_*`` symbols. They are provided by
  ``proxy-libintl`` (``libintl.so.8``, which the published ``libglib-2.0.so``
  already lists as NEEDED), so ``proxy-libintl/0.5`` is a direct requirement
  and ``intl`` is one of the pkg-config modules -- the linker command shows the
  glib recipe does not export ``-lintl`` itself. The musl loader does **not**
  export these symbols (``nm -D /lib/ld-musl-aarch64.so.1`` -> 0 hits), so the
  ``-l:ld-musl-aarch64.so.1`` recipe used by ``archives/a/abr2gbr/1.0.2`` does
  not apply to this call pattern.
* ``PKG_CFLAGS`` is rebuilt too, because the published ``opusfile`` recipe
  installs ``opusfile.h`` into ``<pkg>/include/opus`` but does not export that
  directory from ``package_info().includedirs``: a bare ``#include <opusfile.h>``
  then fails even though opusfile's own shipped ``.pc`` advertises
  ``-I${includedir}/opus``.
* ``PREFIX`` is set to the Conan package folder so the ``PREFIX_RAW`` /
  ``KEW_DATADIR_RAW`` / ``LOCALEDIR_RAW`` macros baked into the binary point at
  the real installation layout (``bin``, ``share/kew``, ``share/locale``).
* Upstream defect: the Makefile's ``SRCS`` names ``src/loader/lyrics.c`` while
  the release tarball only ships ``src/loader/lyrics.cpp``, so a pristine build
  stops on ``No rule to make target 'src/obj/loader/lyrics.o'``.  Patch
  ``0001`` fixes the source suffix and derives the C++ object list.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

# Modules the upstream Makefile resolves through pkg-config (non-Darwin branch,
# i.e. the "else" side of line 118).  ``zlib`` is added because the Makefile
# links ``-lz`` explicitly while relying on the ambient system zlib.
_PKG_MODULES = [
    "gio-2.0",
    "chafa",
    "fftw3f",
    "opus",
    "opusfile",
    "vorbis",
    "vorbisfile",
    "ogg",
    "glib-2.0",
    "taglib",
    "zlib",
    # glib's public headers map the gettext family onto ``g_libintl_*`` and the
    # published glib package only ships (but does not export) that library, so
    # the provider is requested explicitly.
    "intl",
]

# Header sub-directories that a published dependency installs into but does not
# export through ``package_info().includedirs``, so Conan's PkgConfigDeps emits
# ``-I<pkg>/include`` while the dependency's own shipped ``.pc`` emits
# ``-I${includedir}/opus``.  kew includes ``<opusfile.h>`` the way upstream
# distributions ship it, so the missing directory is added here; the dependency
# recipe itself is not touched (it belongs to another PR).
_UNEXPORTED_INCLUDEDIR_SUBDIRS = {
    "opusfile": ("opus",),
}


class KewConan(ConanFile):
    name = "kew"
    version = "4.2.5"
    description = "Kew is a music player for the shell with a terminal user interface."
    license = "GPL-2.0-or-later"
    homepage = "https://codeberg.org/ravachol/kew"
    url = "https://github.com/ravachol/kew"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kew only supports Linux/OHOS, not {}".format(self.settings.os)
            )

    def requirements(self):
        # R26/R32 friendly, runtime-loaded shared dependencies of the produced
        # binary.  ``run=True`` is required: without it Conan does not put the
        # dependency ``.so`` into the consumer run environment, and kew would
        # fail to load them when started from a downstream package.
        self.requires("glib/2.84.0.1", run=True)
        self.requires("chafa/1.18.2", transitive_headers=True, transitive_libs=True, run=True)
        self.requires("fftw3f/3.3.10", transitive_headers=True, run=True)
        self.requires("opus/1.5.2.1", transitive_headers=True, run=True)
        self.requires("opusfile/0.12", transitive_headers=True, transitive_libs=True, run=True)
        self.requires("libvorbis/1.3.7", transitive_headers=True, transitive_libs=True, run=True)
        self.requires("taglib/1.13.1", transitive_headers=True, transitive_libs=True, run=True)
        # Supplies the ``g_libintl_*`` gettext symbols the glib headers expose.
        self.requires("proxy-libintl/0.5", run=True)

        # Version arbitration inside the dependency graph (both alternatives
        # are published; the pin mirrors what the other branch of the graph
        # already resolves to, so no package has to be built from sources):
        #   libogg: opusfile/0.12 pins 1.3.5, libvorbis/1.3.7 pins 1.3.6
        #   zlib:   glib/2.84.0.1 pins 1.3.1.1, taglib/1.13.1 pins 1.3.1
        # Same convention as archives/a/abiword-plugin-docbook/3.0.8.
        self.requires("libogg/1.3.6", override=True, run=True)
        self.requires("zlib/1.3.1.1", override=True, transitive_headers=True, run=True)

        # The Makefile only ever calls ``pkg-config``; it is packaged here so
        # the build does not depend on whatever the worker happens to have.
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        # E392 trap 1: pass an explicit filename so Conan does not guess the
        # archive decoder from the URL tail.
        get(
            self,
            **self.conan_data["sources"],
            filename="kew-4.2.5.tar.gz",
            strip_root=True,
        )

    def generate(self):
        PkgConfigDeps(self).generate()

    def _compilers(self):
        # E392 trap 2 + R33: OHOS ships tools.build:compiler_executables as a
        # dict, read it as a dict and never fall back to a shell $CC.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = (compilers or {}).get("c") or "clang"
        cxx = (compilers or {}).get("cpp") or "clang++"
        return cc, cxx

    def _make_vars(self):
        cc, cxx = self._compilers()
        return " ".join(
            [
                "CC={}".format(cc),
                "CXX={}".format(cxx),
                # See the module docstring: HarmonyOS' ``uname -s`` is not
                # recognised by the Makefile, which would silently drop the
                # PIE/RELRO/BIND_NOW hardening block.
                "UNAME_S=Linux",
                "USE_FAAD=0",
                "STRIP=0",
                "SYMBOLS=0",
                "KEW_VERSION=v{}".format(self.version),
                "PREFIX=\"{}\"".format(self.package_folder),
            ]
        )

    def _extra_includedirs(self):
        extra = []
        for dep_name, subdirs in _UNEXPORTED_INCLUDEDIR_SUBDIRS.items():
            try:
                dep = self.dependencies[dep_name]
            except Exception:  # noqa: BLE001 - absent dep simply contributes nothing
                continue
            for includedir in dep.cpp_info.includedirs or []:
                for sub in subdirs:
                    candidate = os.path.join(includedir, sub)
                    if os.path.isdir(candidate) and candidate not in extra:
                        extra.append(candidate)
        return extra

    def _make_cmd(self, target=""):
        # Upstream links ``$(LIBS) $(LDFLAGS)``, so the ``-L`` directories that
        # pkg-config emits have to be at the head of LIBS; LIBS is therefore
        # rebuilt here with the upstream literal entries appended after it.
        # ``PKG_CONFIG_PATH`` is exported (not used as a command prefix) so the
        # command substitutions below see it as well -- assignments on a simple
        # command are not visible to substitutions inside that same command's
        # own words.  ``PKG_CFLAGS`` keeps pkg-config's output and adds the
        # include directories the dependency recipes forget to export.
        modules = " ".join(_PKG_MODULES)
        extra_inc = "".join(" -I{}".format(d) for d in self._extra_includedirs())
        return (
            "export PKG_CONFIG_PATH=\"{gens}\"; make -j1 {target}"
            " {vars}"
            " PKG_CFLAGS=\"$(pkg-config --cflags {mods}){extra}\""
            " LIBS=\"$(pkg-config --libs {mods})"
            " -lm -lopusfile -lglib-2.0 -lpthread -lstdc++\""
        ).format(
            gens=self.generators_folder,
            target=(target + " ") if target else "",
            vars=self._make_vars(),
            mods=modules,
            extra=extra_inc,
        )

    def build(self):
        apply_conandata_patches(self)
        # E392 trap 3: the bare Makefile lives in the source folder.
        self.run(self._make_cmd(), cwd=self.source_folder, env="conanbuild")

    def package(self):
        # Same variable set as build() so ``make install`` (which depends on
        # ``all``) does not invalidate the objects and does not diverge in the
        # baked PREFIX/datadir macros.
        self.run(
            self._make_cmd("install"),
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

        package_bin = os.path.join(self.package_folder, "bin", "kew")
        self.output.info("kew executable packaged at {}".format(package_bin))
