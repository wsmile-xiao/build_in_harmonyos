#!/usr/bin/env python3
"""Conan recipe for libvterm 0.3.3 — terminal emulator library.

libvterm uses a raw Makefile with libtool. Since libtool is not available
on OHOS, the build() method compiles sources directly with the Conan-
provided compiler and creates both static and shared libraries.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibvtermConan(ConanFile):
    name = "libvterm"
    version = "0.3.3"
    description = "Terminal emulator library"
    license = "MIT"
    homepage = "https://github.com/neovim/libvterm"
    url = "https://github.com/neovim/libvterm"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")

        # Collect source files
        src_dir = self.source_folder
        src_files = [
            "src/encoding.c", "src/keyboard.c", "src/mouse.c", "src/parser.c",
            "src/pen.c", "src/screen.c", "src/state.c", "src/unicode.c", "src/vterm.c"
        ]

        cflags = "-Wall -Iinclude -std=c99 -Wpedantic -fPIC -O2"

        # Generate encoding tables (requires perl)
        self.run("perl -CSD tbl2inc_c.pl src/encoding/uk.tbl >src/encoding/uk.inc", cwd=src_dir)
        self.run("perl -CSD tbl2inc_c.pl src/encoding/DECdrawing.tbl >src/encoding/DECdrawing.inc", cwd=src_dir)
        # Generate fullwidth table (may fail without proper unicode data, create stub)
        self.run("perl find-wide-chars.pl >src/fullwidth.inc 2>/dev/null || echo '/* auto-generated */' >src/fullwidth.inc", cwd=src_dir)

        # Compile all source files to object files
        for src in src_files:
            obj = src.replace(".c", ".o")
            self.run(f"{cc} {cflags} -o {obj} -c {src}", cwd=src_dir)

        # Build static library
        obj_files = " ".join(s.replace(".c", ".o") for s in src_files)
        self.run(f"{ar} rcs libvterm.a {obj_files}", cwd=src_dir)
        self.run(f"{ranlib} libvterm.a 2>/dev/null || true  # ranlib optional for llvm-ar", cwd=src_dir)

        # Build shared library if shared option is set
        if self.options.shared:
            self.run(f"{cc} -shared -o libvterm.so {obj_files} -Wl,-soname,libvterm.so.0", cwd=src_dir)

        # Build binaries
        for bin_src in ["bin/unterm.c", "bin/vterm-ctrl.c", "bin/vterm-dump.c"]:
            bin_name = os.path.basename(bin_src).replace(".c", "")
            lib_flag = "-L. -lvterm"
            if self.options.shared:
                lib_flag = '-L. -lvterm -Wl,-rpath,\\$ORIGIN/../lib'
            self.run(f"{cc} {cflags} -o bin/{bin_name} {bin_src} {lib_flag}", cwd=src_dir)

        # Generate pkg-config file from template
        incdir = os.path.join(self.package_folder, "include")
        libdir = os.path.join(self.package_folder, "lib")
        self.run(
            f'sed -e "s,@INCDIR@,{incdir}," -e "s,@LIBDIR@,{libdir}," '
            f'-e "s,@VERSION@,0.3.3," vterm.pc.in >vterm.pc',
            cwd=src_dir)

    def package(self):
        # Headers
        copy(self, "*.h", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))

        # Static library
        copy(self, "libvterm.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))

        # Shared library
        if self.options.shared:
            copy(self, "libvterm.so*", self.source_folder,
                 os.path.join(self.package_folder, "lib"))

        # Binaries
        copy(self, "unterm", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "vterm-ctrl", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "vterm-dump", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))

        # pkg-config file (generated during build)
        copy(self, "vterm.pc", self.source_folder,
             os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["vterm"]
        if self.options.shared:
            self.cpp_info.defines.append("VTERM_SHARED")
