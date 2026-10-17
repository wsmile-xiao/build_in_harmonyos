#!/usr/bin/env python3
"""Conan recipe for metapixel 1.0.2 - a photomosaic generator.

metapixel is a 1997-2006 C program by Mark Probst / Markus Schani that
generates photomosaics: it splits a source image into a grid of cells and
substitutes the best matching image from a library of constituent images.
It ships three executables:

  * ``metapixel``             - the mosaic generator (main program)
  * ``metapixel-imagesize``   - prints the dimensions of an image
  * ``convert``               - converts a constituent image between the
                                ``.mxt`` table format and the lisp config

Build system: two hand-written Makefiles (no autotools, no cmake, no
configure script).  ``rwimg/`` is built into ``librwimg.a`` and linked into
the other two programs.

The upstream build is 2006-vintage C that reads image-library internals
directly.  Two format backends need API-compat patches before it will
compile against the library versions the registry ships:

* ``patches/0001-rwimg-rwgif-c-giflib5-error-out-parameters.patch`` -
  giflib 5.0 added an ``int *Error`` out-parameter to ``DGifOpenFileName()``
  and ``DGifCloseFile()``; upstream calls the old 1-argument forms.

* ``patches/0002-rwimg-rwpng-c-libpng-opaque-struct-access.patch`` -
  libpng 1.5 made ``png_struct``/``png_info`` opaque, so every direct field
  access in ``rwimg/rwpng.c`` must move to the ``png_get_*`` accessor API,
  and the hand-rolled write-side field block becomes one ``png_set_IHDR()``.

Neither patch uses a platform macro, so both also build unchanged against
glibc-era library versions.  ``rwjpeg.c`` and the remaining sources need no
changes: libjpeg-turbo keeps the libjpeg 6 API surface that 1.0.2 targets.

The two Perl helper scripts shipped upstream (``metapixel-prepare`` and
``metapixel-sizesort``) are installed as-is; they only orchestrate the
``metapixel --prepare`` / ``--print-prepare-settings`` subcommands, so
Perl is not needed to build or to run any delivered functionality.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)


class MetapixelConan(ConanFile):
    name = "metapixel"
    version = "1.0.2"
    description = "Photomosaic generator: rebuilds an image from a library of matching tiles"
    license = "GPL-2.0-or-later"
    homepage = "https://www.complang.tuwien.ac.at/schani/metapixel/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: OHOS must be accepted alongside Linux, never compared with ==.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"metapixel supports Linux and OHOS only, got {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpng/1.6.58.3")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("giflib/5.2.2")
        self.requires("zlib/1.3.2")

    def layout(self):
        # Raw-Makefile project: everything happens in the source folder, so
        # no build/ layout is needed.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: the compiler comes from Conan conf.  The ohos-aarch64 profile
        # carries tools.build:compiler_executables as a dict, and this
        # baseline of conan does not support a ":c" sub-key, so read the
        # whole dict and pick the C entry out of it.
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        cc = compilers.get("c", "clang")

        # The dependency include/lib directories are injected through the
        # make variables the upstream Makefile already uses, so no rule has
        # to be patched.
        include_flags = " ".join("-I" + d for d in self._dep_dirs("includedirs"))
        lib_flags = " ".join("-L" + d for d in self._dep_dirs("libdirs"))
        shared_flags = " ".join("-Wl,-rpath," + d for d in self._dep_dirs("libdirs"))

        # CCOPTS is the variable the upstream Makefile (and rwimg/Makefile)
        # puts in front of every compile; overriding it on the make command
        # line is what actually controls the flags.
        #
        # The version macro needs the value to survive three more shell
        # layers: sh (conan) -> make variable -> recipe shell -> clang.  So
        # the backslashes must still be present when make expands CCOPTS,
        # which is exactly what shlex.quote() gives us here - it wraps the
        # value in single quotes, so sh hands the backslashes through to make
        # untouched and only the final recipe shell removes them.  The
        # compiler then sees -DMETAPIXEL_VERSION="1.0.2" and the macro
        # expands to a real string literal.
        ccopts = " ".join([
            "-I.", "-Irwimg", "-O2", "-Wall",
            '-DMETAPIXEL_VERSION=\\"1.0.2\\"',
            include_flags,
        ])
        ldopts = " ".join([lib_flags, shared_flags])

        # Upstream's default target list includes metapixel.1, which is
        # rebuilt from metapixel.xml with xsltproc + docbook-xsl.  That is a
        # documentation-regeneration step, not a code build step: the release
        # tarball already ships the generated metapixel.1, and the identical
        # file is packaged below.  Skipping it drops two docbook build
        # dependencies and a network-disabled xsltproc invocation without
        # changing a single delivered artifact.  All three code targets are
        # still built.
        targets = ["metapixel", "convert", "metapixel-imagesize"]

        # R9: -j1, never -j$(nproc) - parallel make trips the HMDFS jobserver
        # mkfifo EPERM (E074).
        self.run(shlex.join(
            ["make", f"CC={cc}", f"CCOPTS={ccopts}", f"LDOPTS={ldopts}", "-j1"]
            + targets),
            cwd=self.source_folder)

    def _dep_dirs(self, attr):
        dirs = []
        for dep in self.dependencies.values():
            dirs.extend(getattr(dep.cpp_info, attr))
        # Preserve order while dropping duplicates (zlib is both a direct
        # requirement and a transitive one of libpng).
        seen = set()
        out = []
        for d in dirs:
            if d not in seen:
                seen.add(d)
                out.append(d)
        return out

    def package(self):
        # librwimg.a is deliberately not shipped.  Upstream links it into
        # metapixel and metapixel-imagesize with `$(OBJS) rwimg/librwimg.a`,
        # i.e. statically, so the archive is fully absorbed at link time.
        # `readelf -d` on the delivered binary shows only
        # libpng16.so.16 / libjpeg.so.62 / libgif.so.7 / libc.so as NEEDED -
        # no librwimg - so exporting it would be dead weight.  (Upstream's
        # `zoom` test target also consumes it but is not a delivered
        # artifact: it is a DTEST_ZOOM debugging scratch program.)
        for binary in ("metapixel", "metapixel-imagesize", "convert"):
            copy(self, binary, self.source_folder,
                 os.path.join(self.package_folder, "bin"), keep_path=False)
        # Perl orchestration helpers.  Installed as data: they add no
        # capability that bin/metapixel --prepare does not already provide.
        for script in ("metapixel-prepare", "metapixel-sizesort"):
            copy(self, script, self.source_folder,
                 os.path.join(self.package_folder, "bin"), keep_path=False)
        # Pre-generated man page from the release tarball.
        copy(self, "metapixel.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "metapixelrc", self.source_folder,
             os.path.join(self.package_folder, "share", "metapixel"),
             keep_path=False)

    def package_info(self):
        # Application package: three executables plus their Perl helpers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        bin_dir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.append_path("PATH", bin_dir)
        self.runenv_info.append_path("PATH", bin_dir)
        # Runtime shared libraries (libpng/libjpeg/giflib) are reachable via
        # the rpath baked in at link time, so no LD_LIBRARY_PATH is required.
