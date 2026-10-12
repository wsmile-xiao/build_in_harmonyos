#!/usr/bin/env python3
"""Conan recipe — doas 6.8.2 (OpenBSD doas portable, application).

doas lets a user execute commands as another user after a single config-
driven authorization check.  Upstream (Duncaen/opendoas, the portable
Linux port of OpenBSD doas) ships a hand-written /bin/sh configure plus a
GNUmakefile; there is no generated parser in the repo (parse.y needs
yacc), so this recipe ships the pre-generated parse.c as a recipe asset
and relies on nothing beyond the OHOS native toolchain.

Version identity is the official OpenDoas v6.8.2 tag, not the erroneous
6.9.3 task label used by the predecessor. This is an unvalidated candidate:
the target account database, authentication and privilege-transition
requirements must be proved before claiming functional adaptation.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DoasConan(ConanFile):
    name = "doas"
    version = "6.8.2"
    description = "OpenBSD doas portable — execute commands as another user (shadow auth)"
    license = "ISC"
    homepage = "https://github.com/Duncaen/opendoas"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Pre-generated parser (bison 3.8.2, `bison -y -o parse.c parse.y`):
        # OHOS workers have no yacc/bison, and GNUmakefile turns parse.y
        # into parse.c through make's built-in .y → .c rule.
        copy(self, "parse.c", src=self.recipe_folder,
             dst=os.path.join(self.export_sources_folder))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _bash(self):
        # R5: OHOS workers have no /bin/sh; CONFIG_SHELL is injected by CI,
        # Use the actual supplied executable; do not invent an HNP path.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or shutil.which("bash")
        if not bash or not os.path.isfile(bash):
            raise RuntimeError("A real CONFIG_SHELL, sh or bash executable is required")
        return bash

    # getspnam(3) weak overlay — shipped as an embedded string and written
    # into the source tree by build(): the conan copy()/export pipeline
    # proved unreliable on this CI's cache layout (subunit 65973/66154/
    # 66367 four rounds), and a file the makefile references must exist
    # unconditionally.  See the class docstring of getspnam.c for the
    # rationale; keep this string in sync with patches/0003's expectation.
    _GETSPNAM_SHIM = """/*
 * getspnam(3) weak overlay for OHOS musl.
 *
 * OHOS musl ships <shadow.h> without a getspnam symbol at all (CI 66373:
 * "undefined symbol: getspnam" at link).  This definition is marked weak:
 * on any libc that provides a strong getspnam (glibc, full musl) the
 * linker simply uses theirs and this translation unit contributes
 * nothing; on OHOS the weak one below is linked in.
 *
 * It reads the standard /etc/shadow format (name:hash:...).  On a system
 * without a shadow database (OHOS today) it returns NULL and shadowauth()
 * denies access - the honest behaviour there.
 */
#include <shadow.h>
#include <stdio.h>
#include <string.h>

__attribute__((weak)) struct spwd *getspnam(const char *name)
{
\tstatic struct spwd sp;
\tstatic char line[4096];
\tchar *fields[9];
\tint nf;
\tchar *p;
\tsize_t n;
\tFILE *f;

\tif (name == NULL)
\t\treturn NULL;
\tf = fopen("/etc/shadow", "r");
\tif (f == NULL)
\t\treturn NULL;
\twhile (fgets(line, sizeof(line), f) != NULL) {
\t\tn = strcspn(line, "\\n");
\t\tline[n] = '\\0';
\t\tnf = 0;
\t\tfields[nf++] = line;
\t\tfor (p = line; *p != '\\0' && nf < 9; p++) {
\t\t\tif (*p == ':') {
\t\t\t\t*p = '\\0';
\t\t\t\tfields[nf++] = p + 1;
\t\t\t}
\t\t}
\t\tif (nf < 2)
\t\t\tcontinue;
\t\tif (strcmp(fields[0], name) != 0)
\t\t\tcontinue;
\t\tmemset(&sp, 0, sizeof(sp));
\t\tsp.sp_namp = fields[0];
\t\tsp.sp_pwdp = fields[1];
\t\tfclose(f);
\t\treturn &sp;
\t}
\tfclose(f);
\treturn NULL;
}
"""

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # The exported parse.c lands in the source folder next to parse.y;
        # refresh its mtime so make never regenerates it via yacc.
        os.utime(os.path.join(src, "parse.c"), None)
        # Weak getspnam overlay: write the shim next to its upstream
        # libopenbsd/ siblings (patch 0003 adds the TU to SRCS).
        with open(os.path.join(src, "libopenbsd", "getspnam.c"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(self._GETSPNAM_SHIM)
        # R33: get compiler from Conan conf, never from bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        bash = self._bash()
        # Hand-written sh configure: consumes CC/CFLAGS from the environment
        # and dies on unknown options, so only the options it really knows
        # are passed. Native OS recognition must come from the source patch,
        # not a forced Linux target. --with-shadow selects the backend without PAM
        # (configure probes security/pam_appl.h first and falls back to
        # shadow.h + crypt(3), both inside the OHOS musl libc).
        self.run(
            f'CC="{cc}" "{bash}" ./configure '
            f'--prefix="{self.package_folder}" '
            f"--with-shadow --without-pam",
            cwd=src)
        # R9: always -j1
        self.run(f'CC="{cc}" make -j1', cwd=src)

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        # The binary (upstream installs it suid-root via BINMODE=4755;
        # this candidate ships 0755, preserving the upstream non-setuid
        # rejection. Policy files cannot grant effective UID 0. Do not
        # claim privilege-switch functionality from parser-only tests).
        copy(self, "doas", src, os.path.join(pkg, "bin"))
        os.chmod(os.path.join(pkg, "bin", "doas"), 0o755)
        # Manual pages (upstream install target layout)
        copy(self, "doas.1", src, os.path.join(pkg, "share", "man", "man1"))
        copy(self, "doas.conf.5", src, os.path.join(pkg, "share", "man", "man5"))
        # Example policy next to the Debian-shipped one
        copy(self, "pam.d__doas__linux", src,
             os.path.join(pkg, "share", "doc", "doas", "examples"))
        # License
        copy(self, "LICENSE", src, os.path.join(pkg, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
