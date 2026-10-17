"""Conan recipe — bwbar 1.2.3 (bandwidth bar, single C file + autoconf)"""
import os
from conan import ConanFile
from conan.tools.files import get, copy


class BwbarConan(ConanFile):
    name = "bwbar"
    version = "1.2.3"
    package_type = "application"
    license = "GPL-2.0"
    description = "Bandwidth bar: generates text and graphical readout of bandwidth use"
    homepage = "https://www.kernel.org/pub/software/web/bwbar/"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("libpng/1.6.39")
        self.requires("zlib/1.3.1")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        cc_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = cc_execs.get("c", "cc")
        # bwbar's configure.in uses custom PA_ADD_CFLAGS macros from aclocal.m4;
        # the pre-generated configure script is already in the tarball.
        # Pass Conan dependency paths so configure can find libpng/zlib/m.
        dep_libs = []
        dep_incs = []
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if pf:
                dep_libs.append(os.path.join(pf, "lib"))
                dep_incs.append(os.path.join(pf, "include"))
        ldflags = " ".join(f"-L{d}" for d in dep_libs)
        cppflags = " ".join(f"-I{d}" for d in dep_incs)
        self.run(
            f"CC={cc} CFLAGS='-O2 -fPIC' "
            f"CPPFLAGS='{cppflags}' LDFLAGS='{ldflags}' ./configure",
            cwd=self.source_folder)
        # E114: config.status uses `umask 077 && mktemp -d` which yields
        # unwritable temp dir on HMDFS. Patch after configure generates it.
        self.run("sed -i 's/umask 077/umask 022/' config.status",
                 cwd=self.source_folder)
        # Newer libpng: png_ptr->jmpbuf → png_jmpbuf(png_ptr)
        self.run("sed -i 's/png_ptr->jmpbuf/png_jmpbuf(png_ptr)/g' bwbar.c",
                 cwd=self.source_folder)
        # Newer libpng: need zlib.h for Z_BEST_COMPRESSION
        self.run("sed -i 's|#include <png.h>|#include <png.h>\\n#include <zlib.h>|' bwbar.c",
                 cwd=self.source_folder)
        # MCONFIG is generated from MCONFIG.in by config.status; append our
        # dependency flags so make passes them to the compiler.
        # The Makefile uses $(CC) $(CFLAGS) $(LDFLAGS), so we need CFLAGS not CPPFLAGS.
        inc_flags = " ".join(f"-I{d}" for d in dep_incs)
        self.run(
            f"echo 'CFLAGS += -O2 -fPIC {inc_flags}' >> MCONFIG && "
            f"echo 'LDFLAGS += {ldflags} -lpng -lz -lm' >> MCONFIG",
            cwd=self.source_folder)
        self.run(f"make CC={cc}", cwd=self.source_folder)

    def package(self):
        copy(self, "bwbar", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
