#!/usr/bin/env python3
"""Conan recipe — xworld 2.0 (handwritten Makefile, X11 globe viewer).

xworld displays the Earth as seen from the direction of the Sun, using X11.
Upstream ships a hand-written `configure` + `Makefile.in` (not autoconf-generated).
The build runs two helper programs during compilation:
  - compile_world: reads world.dat, writes world.o (raw pixel data via mmap)
  - pad: page-aligns the ELF binary before world.o is appended

The final binary = ELF (xworld.tmp) + raw data (world.o), concatenated so the
program can mmap its own data segment at runtime.

OHOS adaptation (applied via replace_in_file in build()):
  - compile_world.c: add missing <stdlib.h> / <unistd.h> includes (exit, ftruncate)
  - Makefile.in: link line missing $(LDFLAGS) → added; install target fixed
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, replace_in_file, apply_conandata_patches
from conan.tools.layout import basic_layout


class XworldConan(ConanFile):
    name = "xworld"
    version = "2.0"
    description = "Earth as seen from the direction of the Sun (X11 globe viewer)"
    license = "BSD-4-Clause"
    homepage = "https://pkg.freebsd.org/local-distfiles/naddy/xworld-2.0.tar.gz"
    url = ""
    package_type = "application"
    settings = "os", "arch", "build_type", "compiler"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xworld supports Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libx11/1.8.13")
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        """Export patches (if any) for reproducibility."""
        # No patches for xworld 2.0 — source builds cleanly on OHOS
        pass

    def build(self):
        # Disable safe-delete shim for build commands
        os.environ["CODEBUDDY_SAFE_DELETE_ENABLED"] = "0"
        os.environ.pop("CODEBUDDY_SAFE_DELETE_BIN_DIR", None)
        os.environ.pop("BASH_ENV", None)

        # Apply patches defined in conandata.yml (none for xworld)
        apply_conandata_patches(self)

        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = comp.get("c", "clang") if comp else "clang"

        src = self.source_folder

        # Fix 1: compile_world.c needs <stdlib.h> for exit() and <unistd.h> for ftruncate/fileno/lseek
        compile_world_c = os.path.join(src, "compile_world.c")
        if os.path.isfile(compile_world_c):
            with open(compile_world_c, "r", encoding="utf-8") as fh:
                content = fh.read()
            needs_write = False
            if "#include <stdlib.h>" not in content:
                content = content.replace(
                    "#include <sys/types.h>",
                    "#include <sys/types.h>\n#include <stdlib.h>",
                    1,
                )
                needs_write = True
            if "#include <unistd.h>" not in content:
                content = content.replace(
                    "#include <sys/types.h>",
                    "#include <sys/types.h>\n#include <unistd.h>",
                    1,
                )
                needs_write = True
            if needs_write:
                with open(compile_world_c, "w", encoding="utf-8") as fh:
                    fh.write(content)

        # Fix 1b: pad.c needs <stdlib.h> for exit()
        pad_c = os.path.join(src, "pad.c")
        if os.path.isfile(pad_c):
            with open(pad_c, "r", encoding="utf-8") as fh:
                content = fh.read()
            if "#include <stdlib.h>" not in content:
                content = content.replace(
                    "#include <unistd.h>",
                    "#include <unistd.h>\n#include <stdlib.h>",
                    1,
                )
                with open(pad_c, "w", encoding="utf-8") as fh:
                    fh.write(content)

        # Fix 2: Makefile.in — add $(LDFLAGS) to link line, fix install target
        makefile_in = os.path.join(src, "Makefile.in")
        if os.path.isfile(makefile_in):
            replace_in_file(self, makefile_in,
                "$(MORELIBS) $(LDLIBS)",
                "$(MORELIBS) $(LDFLAGS) $(LDLIBS)",
                strict=False)
            replace_in_file(self, makefile_in,
                "-$(MKDIR) $(BINDIR)",
                "-$(MKDIR) -p $(BINDIR)",
                strict=False)
            replace_in_file(self, makefile_in,
                "$(INSTALL) -m 755 -g bin -o bin xworld $(BINDIR)",
                "$(INSTALL) -m 755 xworld $(BINDIR)",
                strict=False)

        # Aggregate include + lib directories from all transitive deps
        libx11 = self.dependencies["libx11"]
        libx11_inc = os.path.join(libx11.package_folder, "include")
        libx11_lib = os.path.join(libx11.package_folder, "lib")

        inc_dirs = [libx11_inc]
        lib_dirs = [libx11_lib]
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if not pf:
                continue
            dep_inc = os.path.join(pf, "include")
            if os.path.isdir(dep_inc) and dep_inc not in inc_dirs:
                inc_dirs.append(dep_inc)
            dep_lib = os.path.join(pf, "lib")
            if os.path.isdir(dep_lib) and dep_lib not in lib_dirs:
                lib_dirs.append(dep_lib)
        ldflags = " ".join(f"-L{d}" for d in lib_dirs)
        inclflags = " ".join(f"-I{d}" for d in inc_dirs)

        # Package output directory for install target
        pkg_bin = os.path.join(self.package_folder, "bin")

        # Build: make -f Makefile.in (no configure step needed)
        # make -C ${src} ensures cwd is src (needed for ./compile_world, ./pad)
        # All Makefile.in variables passed on command line (CAT/CHMOD/RM/MKDIR/INSTALL required)
        self.run(
            f"make -C {src} -f Makefile.in -j1 "
            f"CC='{cc}' "
            f"CFLAGS='-Wall -O2 -fPIC -I{src}/include' "
            f"INCLUDES='{inclflags}' "
            f"LDFLAGS='{ldflags}' "
            f"LDLIBS='-lm -lX11' "
            f"MORELIBS='' "
            f"STRIP=strip "
            f"CAT=cat "
            f"CHMOD=chmod "
            f"RM=true "
            f"MKDIR='mkdir -p' "
            f"INSTALL='install -m 755' "
            f"BINDIR='{pkg_bin}'",
            env="conanbuild",
        )

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        os.makedirs(os.path.join(pkg, "bin"), exist_ok=True)

        # Copy the built xworld binary
        xworld_bin = os.path.join(src, "xworld")
        if os.path.isfile(xworld_bin):
            shutil.copy2(xworld_bin, os.path.join(pkg, "bin", "xworld"))

        # Extract license from source header
        lic_dir = os.path.join(pkg, "licenses")
        os.makedirs(lic_dir, exist_ok=True)
        src_xworld_c = os.path.join(src, "xworld.c")
        if os.path.isfile(src_xworld_c):
            with open(src_xworld_c, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
            lic_lines = []
            in_comment = False
            for line in lines:
                s = line.strip()
                if s.startswith("/*"):
                    in_comment = True
                if in_comment:
                    lic_lines.append(line)
                    if s.endswith("*/"):
                        break
            if lic_lines:
                with open(os.path.join(lic_dir, "xworld.COPYRIGHT"), "w") as fh:
                    fh.writelines(lic_lines)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
