#!/usr/bin/env python3
"""Conan recipe for lcc 4.2 — retargetable C compiler (drh/lcc).

lcc 4.2 uses its own makefile (no configure). Build:
    make BUILDDIR=<bld> CC=<cc> HOSTFILE=etc/linux.c all

The driver (etc/linux.c) locates its components relative to LCCDIR via
-Wo-lccdir=: rcc, include/, gcc/cpp, liblcc.a. OHOS has no gcc, so a
clang-cpp wrapper is installed at <lccdir>/gcc/cpp and the dist include
headers are copied into <lccdir>/include (see notes.md).

Package layout (consumer-usable as a compiler tool):
    bin/lcc bin/rcc bin/cpp bin/lburg bin/bprint   (executables)
    lib/lcc/rcc   lib/lcc/include/*.h   lib/lcc/gcc/cpp   lib/lcc/liblcc.a
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, mkdir, copy
from conan.tools.layout import basic_layout


class LccConan(ConanFile):
    name = "lcc"
    version = "4.2"
    description = "lcc 4.2 - retargetable C compiler (Chris Fraser & David Hanson)"
    license = "SGI-B-2.0"
    homepage = "https://github.com/drh/lcc"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # lcc 4.2 is a self-contained C compiler distribution; no external deps.
        pass

    def _write_cpp_wrapper(self, path):
        """Install a preprocessor wrapper at <lccdir>/gcc/cpp.

        lcc's driver invokes it as: cpp [opts] <src> [<out.i>]; clang-cpp
        expects "-o out" / stdin, so translate the call form.
        """
        with open(path, "w") as f:
            f.write("#!/bin/sh\n")
            f.write("# lcc driver compose call: cpp [opts] <src> [<out.i>]\n")
            f.write('src=""; out=""; opts=\n')
            f.write("for a in \"$@\"; do\n")
            f.write("  case \"$a\" in\n")
            f.write("    -*) opts=\"$opts $a\" ;;\n")
            f.write('    *) if [ -f "$a" ]; then src="$a"; elif [ -z "$out" ]; then out="$a"; fi ;;\n')
            f.write("  esac\n")
            f.write("done\n")
            f.write('if command -v clang-cpp >/dev/null 2>&1; then CPP=clang-cpp\n')
            f.write('elif command -v clang >/dev/null 2>&1; then CPP="clang -E -x c"\n')
            f.write('else CPP="cc -E -x c"; fi\n')
            f.write('if [ -n "$out" ]; then exec $CPP $opts -o "$out" "$src";\n')
            f.write('else exec $CPP $opts "$src"; fi\n')
        os.chmod(path, 0o755)

    def build(self):
        apply_conandata_patches(self)
        bld = os.path.join(self.build_folder, "lcc-bld")
        mkdir(self, bld)
        # lccdir scaffolding inside the build dir (mirrors final lib/lcc)
        lccdir = os.path.join(bld, "lccdir")
        mkdir(self, os.path.join(lccdir, "include"))
        mkdir(self, os.path.join(lccdir, "gcc"))
        src = self.source_folder
        for h in ("assert.h", "float.h", "limits.h", "math.h", "stdarg.h"):
            hp = os.path.join(src, "include", "x86", "linux", h)
            if os.path.isfile(hp):
                copy(self, h, os.path.dirname(hp), os.path.join(lccdir, "include"))
        self._write_cpp_wrapper(os.path.join(lccdir, "gcc", "cpp"))
        # ccache disabled (R49/verification hygiene) not needed; plain build
        self.run(
            "make BUILDDIR={0} CC=clang HOSTFILE=etc/linux.c all".format(bld),
            cwd=src,
        )

    def package(self):
        bld = os.path.join(self.build_folder, "lcc-bld")
        bindir = os.path.join(self.package_folder, "bin")
        lccdir = os.path.join(self.package_folder, "lib", "lcc")
        mkdir(self, bindir)
        mkdir(self, os.path.join(lccdir, "include"))
        mkdir(self, os.path.join(lccdir, "gcc"))
        for exe in ("lcc", "rcc", "cpp", "lburg", "bprint"):
            p = os.path.join(bld, exe)
            if os.path.isfile(p):
                copy(self, exe, bld, bindir)
                copy(self, exe, bld, lccdir)  # driver resolves via -Wo-lccdir
        # include headers + cpp wrapper + static runtime libs into lccdir
        bld_lccdir = os.path.join(bld, "lccdir")
        copy(self, "*.h", os.path.join(bld_lccdir, "include"), os.path.join(lccdir, "include"))
        copy(self, "cpp", os.path.join(bld_lccdir, "gcc"), os.path.join(lccdir, "gcc"))
        for lib in ("liblcc.a", "librcc.a"):
            p = os.path.join(bld, lib)
            if os.path.isfile(p):
                copy(self, lib, bld, lccdir)
        # keep a copy of libs in lib/ as well
        for lib in ("liblcc.a", "librcc.a"):
            p = os.path.join(lccdir, lib)
            if os.path.isfile(p):
                copy(self, lib, lccdir, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        # lccdir for consumers (driver's -Wo-lccdir default location)
        self.conf_info.define("user.lcc:lccdir", os.path.join(self.package_folder, "lib", "lcc"))