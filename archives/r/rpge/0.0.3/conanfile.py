#!/usr/bin/env python3
"""Conan recipe for GNU RPGE 0.0.3 on HarmonyOS PC."""

import os
import shlex

from conan import ConanFile
from conan.tools.files import (
    copy,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RpgeConan(ConanFile):
    name = "rpge"
    version = "0.0.3"
    description = "GNU engine for two-dimensional graphical role-playing games"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/rpge/"
    url = "https://ftp.gnu.org/gnu/rpge/rpge-0.0.3.tar.gz"
    package_type = "application"
    exports_sources = "compat/libguile.h"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # RPGE uses the SDL 1.2 API. On OHOS, sdl12-compat supplies that ABI
        # while SDL_image 1.2 and SDL_ttf 2.0.11 are built against the same ABI.
        self.requires("guile/2.2.7.1", run=True)
        # Guile's published headers include gmp.h, but its package metadata
        # does not expose GMP as a direct dependency.
        self.requires("gmp/6.3.0")
        self.requires("sdl12-compat/1.2.68", run=True)
        self.requires("sdl-image/1.2.12", run=True)
        self.requires("sdl_ttf/2.0.11", run=True)
        # SDL_image's 4.7.Z range otherwise resolves the older libtiff recipe,
        # which selects libjpeg/9f and conflicts with SDL_image's libjpeg-turbo.
        self.requires("libtiff/4.7.2.1", override=True)
        # The compatible published libtiff binary is pinned to zlib 1.3.1.1;
        # the SDL_image codec ranges also accept that same OHOS zlib build.
        self.requires("zlib/1.3.1.1", override=True)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        copy(
            self,
            "libguile.h",
            src=os.path.join(self.recipe_folder, "compat"),
            dst=os.path.join(self.source_folder, "compat"),
        )

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
                "--prefix=/usr",
                # These standard allocation functions are present on OHOS;
                # Autoconf cannot run its probes while cross compiling and
                # otherwise selects unbuilt gnulib replacements.
                "ac_cv_func_malloc_0_nonnull=yes",
                "ac_cv_func_realloc_0_nonnull=yes",
            ]
        )

        # The old project hard-codes SDL 1.2-era library names, while the
        # published OHOS compatibility packages expose SDL-1.2 and guile-2.2.
        # Carry every resolved dependency directory into this legacy configure.
        include_dirs = []
        lib_dirs = []
        link_libs = []
        for dependency in self.dependencies.values():
            if not dependency.package_folder:
                continue
            for include_dir in dependency.cpp_info.includedirs:
                path = os.path.join(dependency.package_folder, include_dir)
                if path not in include_dirs:
                    include_dirs.append(path)
                if os.path.basename(include_dir) == "SDL":
                    parent = os.path.join(dependency.package_folder, "include")
                    if parent not in include_dirs:
                        include_dirs.append(parent)
            for lib_dir in dependency.cpp_info.libdirs:
                path = os.path.join(dependency.package_folder, lib_dir)
                if path not in lib_dirs:
                    lib_dirs.append(path)
            for library in dependency.cpp_info.libs or []:
                flag = f"-l{library}"
                if flag not in link_libs:
                    link_libs.append(flag)
            for library in dependency.cpp_info.system_libs or []:
                flag = f"-l{library}"
                if flag not in link_libs:
                    link_libs.append(flag)
        sdl12 = self.dependencies["sdl12-compat"]
        sdl_parent = os.path.join(sdl12.package_folder, "include")
        if sdl_parent not in include_dirs:
            include_dirs.append(sdl_parent)
        # Guile's compatibility umbrella header includes gmp.h; this version
        # of the GMP recipe does not publish cpp_info.includedirs reliably.
        gmp_include = os.path.join(self.dependencies["gmp"].package_folder, "include")
        if gmp_include not in include_dirs:
            include_dirs.append(gmp_include)
        include_dirs.append(os.path.join(self.source_folder, "compat"))
        tc.configure_args.append(
            "CPPFLAGS=" + shlex.join([f"-I{path}" for path in include_dirs])
        )
        tc.configure_args.append(
            "LDFLAGS=" + shlex.join([f"-L{path}" for path in lib_dirs])
        )
        if "-lpthread" not in link_libs:
            link_libs.append("-lpthread")
        tc.configure_args.append("LIBS=" + shlex.join(link_libs))
        tc.generate()

    def build(self):
        config_sub = os.path.join(self.source_folder, "config.sub")
        replace_in_file(
            self,
            config_sub,
            "linux-gnu* | linux-android* | linux-dietlibc",
            "linux-gnu* | linux-android* | linux-ohos* | linux-dietlibc",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "-lguile",
            "-lguile-2.2",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
        )
        replace_in_file(
            self,
            config_sub,
            "-linux-gnu* | -linux-android* \\",
            "-linux-gnu* | -linux-android* | -linux-ohos* \\",
        )
        replace_in_file(
            self,
            config_sub,
            "\t-linux-dietlibc)\n\t\tos=-linux-dietlibc\n\t\t;;\n\t-linux*)",
            "\t-linux-dietlibc)\n\t\tos=-linux-dietlibc\n\t\t;;\n\t-linux-ohos*)\n\t\tos=-linux-ohos\n\t\t;;\n\t-linux*)",
        )
        # gnulib's bundled error.c expects non-glibc programs to provide this.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "main.c"),
            '#include "main.h"',
            '#include "main.h"\n\nchar *program_name = "rpge";',
        )
        # Remove the stale global LIBS assignment so configure's Conan-resolved
        # libraries (including transitive static dependencies) reach the link.
        for makefile in ("src/Makefile.in",):
            path = os.path.join(self.source_folder, makefile)
            with open(path, encoding="utf-8") as stream:
                contents = stream.read()
            contents = contents.replace(
                "LIBS = -lpthread -lguile -lSDL -lSDL_ttf -lSDL_image\n", ""
            )
            contents = contents.replace(" -pg", "")
            with open(path, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(contents)

        # GNU makeinfo and texi2pdf are host documentation tools, not target
        # runtime dependencies.  The release tarball's generated Makefile.in
        # lists documentation as part of `all`, so skip only that subdirectory.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "Makefile.in"),
            "SUBDIRS = lib scm doc images src conf examples",
            "SUBDIRS = lib scm images src conf examples",
        )

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses", "rpge"))

    def package_info(self):
        self.cpp_info.bindirs = ["usr/bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "usr", "bin"))
