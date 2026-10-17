#!/usr/bin/env python3
"""Conan recipe for ncompress 5.0 — classic Unix LZW `compress` (single-file C).

Upstream (github.com/vapier/ncompress) ships a small GNU Make wrapper
(GNUmakefile -> Makefile.def) but the product is a single translation unit,
compress.c. We compile it directly with the exact flags upstream injects
(-DUSERMEM=800000, plus -DUTIME_H -DLSTAT added by GNUmakefile when it
generates Makefile), then run the official upstream test suite
(tests/runtests.sh == upstream `make check`).

License: Unlicense (public-domain dedication, LICENSE.txt/UNLICENSE).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (copy, export_conandata_patches, get,
                               replace_in_file)
from conan.tools.layout import basic_layout


class NcompressConan(ConanFile):
    name = "ncompress"
    version = "5.0"
    description = "A fast, simple LZW file compressor (the classic Unix compress tool)."
    license = "Unlicense"
    homepage = "https://github.com/vapier/ncompress"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must be an explicit allow-list
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ncompress supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)
        # ncompress is a single-file tool that builds in-source.
        self.folders.build = "."

    def source(self):
        # The primary codeload URL is extension-less, so give Conan an explicit
        # .tar.gz filename to pick the right decompressor (BadZipFile otherwise).
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="ncompress-5.0.tar.gz")

    def _cc(self):
        # R33: take the compiler from Conan conf, never a bare env var
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        return compilers.get("c", "clang") if compilers else "clang"

    def _shell(self):
        # R5: OHOS has no guaranteed /bin/sh for complex scripts; use CONFIG_SHELL
        # (profile [buildenv]) and fall back to bash.
        return os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"

    def build(self):
        cc = self._cc()
        # Upstream Makefile.def compile rule (GNUmakefile injects -DUTIME_H -DLSTAT):
        #   $(CC) -o compress $(options) compress.c $(LBOPT)
        #   options = $(CFLAGS) $(CPPFLAGS) -DUSERMEM=800000
        self.run(
            f"{cc} -O2 -g -Wall -DUSERMEM=800000 -DUTIME_H -DLSTAT "
            f"-o compress compress.c",
            cwd=self.source_folder,
        )
        # L1c: run the official upstream test suite (make check -> tests/runtests.sh).
        # COMPRESS points at the freshly built binary; TMPDIR kept inside the build
        # folder to avoid relying on a world-writable /tmp on OHOS.
        shell = self._shell()
        compress = os.path.join(self.source_folder, "compress")
        tmpdir = self.build_folder
        # OHOS /tmp is read-only. runtests.sh clears TMPDIR and calls bare
        # `mktemp -d` (defaults to /tmp). Patch it to honour an inherited TMPDIR.
        patched = set()
        for base in (self.source_folder, self.build_folder):
            harness = os.path.join(base, "tests", "runtests.sh")
            if os.path.isfile(harness) and os.path.realpath(harness) not in patched:
                patched.add(os.path.realpath(harness))
                replace_in_file(self, harness, 'TMPDIR=""',
                                'TMPDIR="${TMPDIR:-/tmp}"')
                replace_in_file(self, harness,
                                'TMPDIR="$(mktemp -d)"',
                                'TMPDIR="$(mktemp -d "${TMPDIR}/tmp.XXXXXX")"')
        self.run(
            f"TMPDIR={tmpdir} COMPRESS={compress} {shell} tests/runtests.sh",
            cwd=self.source_folder,
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(mandir, exist_ok=True)
        src = self.source_folder

        # compress binary plus the classic argv[0]-based aliases uncompress/zcat
        # (upstream creates them with hard links; copies behave identically because
        # the program chooses mode from argv[0]).
        for name in ("compress", "uncompress", "zcat"):
            shutil.copy2(os.path.join(src, "compress"), os.path.join(bindir, name))
        # helper shell scripts installed by upstream `make install_extra`
        for script in ("zcmp", "zdiff", "zmore"):
            shutil.copy2(os.path.join(src, script), os.path.join(bindir, script))
        # man pages
        for man in ("compress.1", "uncompress.1", "zcmp.1", "zmore.1"):
            shutil.copy2(os.path.join(src, man), os.path.join(mandir, man))
        # license file (Unlicense public-domain dedication)
        copy(self, "UNLICENSE", src=src,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # ncompress is a CLI tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
