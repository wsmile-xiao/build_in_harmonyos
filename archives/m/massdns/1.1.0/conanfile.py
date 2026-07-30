#!/usr/bin/env python3
"""Conan recipe for massdns 1.1.0 — high-performance DNS stub resolver.

MassDNS is a simple high-performance DNS stub resolver targeting those who
seek to resolve a massive amount of domain names. It is a command-line tool
built with a plain Makefile (no configure script, no make install target).

Build: make → bin/massdns (single C file: src/main.c)
Deps:  None external (custom DNS implementation, no ldns dependency)

See: https://github.com/blechschmidt/massdns
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MassdnsConan(ConanFile):
    name = "massdns"
    version = "1.1.0"
    description = "High-performance DNS stub resolver for batch DNS resolution"
    license = "GPL-3.0-only"
    homepage = "https://github.com/blechschmidt/massdns"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external Conan deps: massdns uses a custom DNS implementation
        # (no ldns dependency since v0.3).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        # Conan 2 stores the whole dict under tools.build:compiler_executables
        # (there is no tools.build:compiler_executables:c sub-key).
        # The Makefile uses $(CC) which defaults to "cc" if unset; we must
        # explicitly pass the OHOS cross-compiler from the Conan toolchain.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # massdns Makefile: PROJECT_FLAGS uses `git describe` which fails in
        # tarball (no .git) — pass REVISION explicitly to avoid build error.
        # main.c uses MASSDNS_REVISION as a %s arg in fprintf, so the macro
        # MUST expand to a C string literal "1.1.0" (with double quotes).
        # Two shell layers (self.run → make recipe) strip unescaped quotes.
        # Python source \\\" → runtime \" → (layer1 single-quoted, preserved)
        # → layer2 shell unescapes to " → clang sees "1.1.0" string literal.
        # R9: Always use -j1.
        self.run(
            f"make -C {self.source_folder} CC={cc} "
            f"PROJECT_FLAGS='-DMASSDNS_REVISION=\\\"1.1.0\\\"' -j1"
        )

    def package(self):
        # massdns produces a single binary in {source_folder}/bin/
        copy(self, "massdns", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        # Man page
        copy(self, "massdns.1", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

        # R38/E082: HarmonyOS requires ELF signing before a binary can execute.
        # Without this the test_package cannot run the massdns binary.
        # R32: guard with in ("Linux", "OHOS") — signing only needed on OHOS,
        # but package() runs in the host context so we sign for OHOS targets.
        bin_path = os.path.join(self.package_folder, "bin", "massdns")
        if os.path.exists(bin_path) and self.settings.os in ("Linux", "OHOS"):
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            if os.path.exists(sign_tool):
                tmp_signed = bin_path + ".signed"
                # .codesign section may not exist on a fresh build — tolerate failure
                self.run(f"{objcopy} --remove-section .codesign {bin_path} || true", quiet=True)
                self.run(f"{sign_tool} sign -inFile {bin_path} -outFile {tmp_signed} "
                         f"-selfSign 1", quiet=True)
                os.replace(tmp_signed, bin_path)
                os.chmod(bin_path, 0o755)

    def package_info(self):
        # Application — no libraries, just a binary in bin/
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
