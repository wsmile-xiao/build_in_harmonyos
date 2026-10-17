#!/usr/bin/env python3
"""Conan recipe for rgbds 1.0.1 (Rednex Game Boy Development System).

rgbds is a free assembly toolchain for the Nintendo Game Boy and Game Boy
Color, providing four command-line programs:

- ``rgbasm``  — assembler
- ``rgblink`` — linker
- ``rgbfix``  — ROM header fixer
- ``rgbgfx``  — PNG-to-Game-Boy graphics converter

Build system: the upstream GNU Makefile. The GitHub tag archive does not
ship the Bison-generated parser sources (``src/asm/parser.*`` and
``src/link/script.*``), so bison is a build requirement. Only ``rgbgfx``
links libpng; the flags are taken straight from the libpng dependency so no
pkg-config tool is needed at build time.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class RgbdsConan(ConanFile):
    name = "rgbds"
    version = "1.0.1"
    description = "Rednex Game Boy Development System — an assembly toolchain for the Nintendo Game Boy and Game Boy Color"
    license = "MIT"
    homepage = "https://rgbds.gbdev.io/"
    url = "https://github.com/gbdev/rgbds"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpng/1.6.58.2")

    def build_requirements(self):
        self.tool_requires("bison/3.8.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rgbds is supported only on Linux and OHOS, not {self.settings.os}"
            )
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration(
                f"rgbds is packaged for the aarch64 target, not {self.settings.arch}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)

        # R33: get the compiler from Conan conf, never from a bare shell env var.
        comps = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = comps.get("cpp") or "clang++"

        # The tag archive ships only the .y grammars, so generate the two Bison
        # parsers up front. This bypasses src/bison.sh, which shells out to
        # `sed -E` (unreliable on toybox) and expects /bin/sh.
        #
        # bison/3.8.2's compiled-in datadir is wrong (it looks for its m4
        # macros under /share/bison), so point BISON_PKGDATADIR at the m4
        # macros inside the bison package itself.
        bison_pkg = self.dependencies.build["bison"].package_folder
        bison_datadir = os.path.join(bison_pkg, "share", "bison")
        bison_flags = (
            "-Wall -Dlr.type=ielr -Dparse.lac=full "
            "-Dapi.token.raw=true -Dparse.error=detailed -Wcounterexamples"
        )
        self.run(
            f'BISON_PKGDATADIR="{bison_datadir}" '
            f'bison {bison_flags} -d -o src/asm/parser.cpp src/asm/parser.y',
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run(
            f'BISON_PKGDATADIR="{bison_datadir}" '
            f'bison {bison_flags} -d -o src/link/script.cpp src/link/script.y',
            cwd=self.source_folder,
            env="conanbuild",
        )

        # libpng flags straight from the dependency (only rgbgfx needs them).
        # Conan may expose includedirs/libdirs as package-relative paths, so
        # resolve them against the package folder before emitting -I/-L.
        png_pkg = self.dependencies["libpng"].package_folder
        png = self.dependencies["libpng"].cpp_info

        def _abs(paths):
            return [
                path if os.path.isabs(path) else os.path.join(png_pkg, path)
                for path in paths
            ]

        png_cflags = " ".join(f"-I{d}" for d in _abs(png.includedirs))
        png_ldflags = " ".join(f"-L{d}" for d in _abs(png.libdirs))
        png_ldlibs = " ".join(f"-l{l}" for l in png.libs)

        # CXXFLAGS drops upstream's `-flto` (the cross LTO plugin is not
        # available in the OHOS toolchain). STRIP=true keeps the binaries
        # unstripped: the OHOS MAC rejects stripped ELF binaries at exec time.
        # PKG_CONFIG=true makes the Makefile's backtick probe a no-op because
        # the real libpng flags are passed explicitly below.
        self.run(
            f'make -j1 CXX="{cxx}" CXXFLAGS="-O2 -DNDEBUG" STRIP=true '
            f'PKG_CONFIG=true '
            f'PNGCFLAGS="{png_cflags}" PNGLDFLAGS="{png_ldflags}" PNGLDLIBS="{png_ldlibs}"',
            cwd=self.source_folder,
            env="conanbuild",
        )

        # Run the upstream internal regression suite (asm/link/fix/gfx test.sh).
        # TMPDIR must be writable (OHOS /tmp is read-only, E002); the gfx test
        # helpers need the libpng flags (patch 0002 forwards them from the env).
        # Use CONFIG_SHELL (bash) because the OHOS login shell lacks bash.
        test_tmp = os.path.join(self.build_folder, ".test-tmp")
        os.makedirs(test_tmp, exist_ok=True)
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # rgbgfx is dynamically linked against libpng16.so, so the gfx tests
        # need the libpng lib dir on the runtime search path (E019).
        png_libdir = os.path.join(png_pkg, "lib")
        self.run(
            f'TMPDIR="{test_tmp}" PNGCFLAGS="{png_cflags}" '
            f'PNGLDFLAGS="{png_ldflags}" PNGLDLIBS="{png_ldlibs}" '
            f'LD_LIBRARY_PATH="{png_libdir}" '
            f'{shell} test/run-tests.sh --only-internal',
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        # Copy binaries directly: the upstream `make install` target relies on
        # the GNU `install` command, which toybox does not provide (E098).
        for tool in ("rgbasm", "rgblink", "rgbfix", "rgbgfx"):
            copy(
                self,
                tool,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "bin"),
            )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        for section, glob in (("man1", "*.1"), ("man5", "*.5"), ("man7", "*.7")):
            copy(
                self,
                glob,
                src=os.path.join(self.source_folder, "man"),
                dst=os.path.join(self.package_folder, "share", "man", section),
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
