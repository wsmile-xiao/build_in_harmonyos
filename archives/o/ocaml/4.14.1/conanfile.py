#!/usr/bin/env python3
"""Conan recipe — OCaml 4.14.1

OCaml uses a custom configure script (not autotools) and a bootstrap
compilation process. Key platform adaptations for OHOS:
  - config.guess patched to recognize HarmonyOS as linux-gnu
  - ASM set to 'clang -c' (not llvm-as, which expects LLVM IR)
  - TMPDIR used for configure temp directories
  - config.status patched to use mkdir instead of mktemp (OHOS permission fix)
  - boot/ocamlrun copy uses rm -f && cp (HMDFS workaround)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file

class OcamlConan(ConanFile):
    name = "ocaml"
    version = "4.14.1"
    description = "OCaml is a functional, statically-typed language from the ML family"
    license = "LGPL-2.1"
    homepage = "https://ocaml.org"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # OCaml has no external Conan dependencies

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass  # OCaml uses custom configure, not autotools toolchain

    def build(self):
        apply_conandata_patches(self)
        # prefix is set to package_folder; DESTDIR staging in package() handles the rest
        prefix = self.package_folder
        # Step 1: Run configure with --no-create to generate config.status without executing it
        self.run(f"./configure --prefix={prefix} --no-create", env="conanrun")
        # Step 2: Patch config.status to fix OHOS temp directory permission issue
        # mktemp -d creates dirs with umask 077 which OHOS /bin/sh cannot write to
        # Replace with a simple mkdir-based approach
        replace_in_file(self, "config.status",
            'tmp=`(umask 077 && mktemp -d "${TMPDIR:-./}/confXXXXXX") 2>/dev/null` &&\n  test -d "$tmp"',
            'tmp="${TMPDIR:-.}/cs.$$" &&\n  rm -rf "$tmp" && mkdir -p "$tmp" && test -d "$tmp"')
        replace_in_file(self, "config.status",
            'tmp=${TMPDIR:-.}/conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
            'tmp="${TMPDIR:-.}/cs.$$"\n  rm -rf "$tmp" && mkdir -p "$tmp"')
        # Step 3: Run config.status manually
        self.run("/bin/sh ./config.status", env="conanrun")
        # Step 4: Fix ASM: llvm-as expects LLVM IR, but OCaml generates GAS assembly
        replace_in_file(self, "Makefile.config", "ASM=llvm-as", "ASM=clang -c")
        # Step 5: Pre-remove boot/ocamlrun to avoid HMDFS cp permission error
        boot_ocamlrun = os.path.join(self.source_folder, "boot", "ocamlrun")
        if os.path.exists(boot_ocamlrun):
            os.remove(boot_ocamlrun)
        # Step 6: Disable manpages generation (ocamldoc.opt triggers OHOS security popup)
        replace_in_file(self, "Makefile.config", "STDLIB_MANPAGES=true", "STDLIB_MANPAGES=false")
        # Step 7: Bootstrap compilation with -j1
        self.run("make -j1", env="conanrun")

    def package(self):
        # Use temp DESTDIR to avoid nested directory structure.
        # OCaml configure set prefix=self.package_folder, so
        # make install DESTDIR=X creates files at X/<prefix>/
        dest = os.path.join(self.build_folder, "dest_install")
        self.run(f'make install DESTDIR="{dest}"', env="conanrun")
        # Copy from dest/<prefix>/ to package_folder (top-level layout)
        prefix = self.package_folder
        src_base = os.path.join(dest, prefix.lstrip("/"))
        if not os.path.isdir(src_base):
            src_base = dest
        copy(self, "*", src_base, self.package_folder)

    def package_info(self):
        self.cpp_info.libs = ["camlrun", "camlasm"]
        self.cpp_info.includedirs = ["lib/ocaml/caml"]
