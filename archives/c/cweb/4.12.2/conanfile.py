#!/usr/bin/env python3
"""Conan recipe for cweb 4.12.2 — C/C++/Java literate programming system.

cweb is a bootstrap compiler: ctangle is compiled from C source, then used to
generate cweave.c from cweave.w. On OHOS, newly compiled ELF binaries must be
signed (binary-sign-tool) before they can be executed by the kernel.

Platform adaptations:
  1. Makefile patch (0001-Makefile.patch): DESTDIR renamed to BINDIR, added
     PREFIX and standard DESTDIR for staging install; CFLAGS/LINKFLAGS use
     ?= override syntax for OHOS-compatible defaults.
  2. Bootstrap ELF signing: ctangle must be signed after compilation so it
     can execute to generate cweave.c (E077/E135 knowledge).
  3. LINKFLAGS: -fuse-ld=ld.bfd to avoid lld's libxml2 dependency (E105).

R32: settings.os check uses == "OHOS" (specific platform check, not exclusion).
R33: Compiler obtained from Conan conf, not shell env vars.
R34: test_package runs ctangle/cweave on a real .w file.
R38: commands.json declared at software level (tool type).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CwebConan(ConanFile):
    name = "cweb"
    version = "4.12.2"
    description = "C/C++/Java literate programming documentation system (ctangle and cweave)"
    license = "Knuth-CTAN"
    homepage = "https://github.com/ascherer/cweb"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

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

        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = comp_execs.get("c", "clang")
        src = self.source_folder

        # Step 1: Build ctangle (bootstrap compiler from .c source)
        self.run(f"make ctangle CC={cc} -j1", cwd=src)

        # Step 2: Sign ctangle for OHOS ELF execution
        # cweb is a bootstrap compiler: ctangle must execute to generate cweave.c
        if self.settings.os == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            ctangle_path = os.path.join(src, "ctangle")
            self.run(f'{sign_tool} sign -inFile "{ctangle_path}" -outFile "{ctangle_path}" -selfSign 1', cwd=src)
            self.run(f'chmod a+x "{ctangle_path}"', cwd=src)

        # Step 3: Build cweave (ctangle generates cweave.c from cweave.w, then compiles)
        self.run(f"make cweave CC={cc} -j1", cwd=src)

        # Step 4: Sign cweave for OHOS ELF execution
        if self.settings.os == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            cweave_path = os.path.join(src, "cweave")
            self.run(f'{sign_tool} sign -inFile "{cweave_path}" -outFile "{cweave_path}" -selfSign 1', cwd=src)
            self.run(f'chmod a+x "{cweave_path}"', cwd=src)

    def package(self):
        # Copy executables
        copy(self, "ctangle", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "cweave", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Copy CWEB input library files
        copy(self, "c++lib.w", self.source_folder, os.path.join(self.package_folder, "lib", "cweb"))
        copy(self, "iso_types.w", self.source_folder, os.path.join(self.package_folder, "lib", "cweb"))
        # Copy TeX macro files
        copy(self, "cwebmac.tex", self.source_folder, os.path.join(self.package_folder, "share", "texmf", "tex", "generic"))
        copy(self, "cwebacromac.tex", self.source_folder, os.path.join(self.package_folder, "share", "texmf", "tex", "generic"))
        # Copy man page and emacs mode
        copy(self, "cweb.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "cweb.el", self.source_folder, os.path.join(self.package_folder, "share", "emacs", "site-lisp"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
