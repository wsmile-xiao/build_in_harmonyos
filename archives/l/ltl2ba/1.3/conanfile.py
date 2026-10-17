#!/usr/bin/env python3
"""Conan recipe for ltl2ba (LTL to Büchi automata translator) — custom Makefile build.

ltl2ba is a command-line tool, not a library. It translates an LTL formula
into a never claim (a Büchi automaton) for the Spin model checker. The
upstream project ships a plain Makefile (no CMake, no autotools configure
script) and the generated parser/lexer (parse.c / lex.c) are hand-written
C, so no flex/bison toolchain is required.

The Makefile uses `CC=gcc` and `CFLAGS=-O3 -ansi -DNXT` by default; this
recipe overrides CC/CFLAGS from the Conan toolchain (R33) and builds the
single `ltl2ba` executable. Zero source patches are needed — all includes
are standard POSIX headers available on HarmonyOS.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class Ltl2baConan(ConanFile):
    name = "ltl2ba"
    version = "1.3"
    description = "Fast translation from LTL formulae to Büchi automata"
    license = "GPL-2.0-or-later"
    homepage = "https://lsv.ens-paris-saclay.fr/~gastin/ltl2ba/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No CMake/autotools — the Makefile reads CC/CFLAGS from the
        # environment. AutotoolsToolchain (or similar) is not applicable.
        # Conan's VirtualBuildEnv already exports CC/CFLAGS/LDFLAGS from the
        # profile settings + tools.build:compiler_executables, so the plain
        # `make` invocation in build() picks them up via conanbuild env.
        pass

    def _get_cc(self):
        # R33: Get compiler from Conan conf, not undefined shell variables
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return comp_execs.get("c") or "clang"

    def _sdk_llvm_libdir(self):
        """LLVM lib dir of the active compiler toolchain (libxml2.so.16).

        The OHOS clang driver spawns `lld` for linking, and lld's RUNPATH
        ($ORIGIN/../lib) points into the SDK llvm/lib. On CI workers the
        ambient LD_LIBRARY_PATH can shadow that dir with an incompatible
        libxml2.so.16, making lld fail at start with "Error loading shared
        library libxml2.so.16 ... symbol not found" (xmlFreeDoc /
        xmlReadMemory / xmlDocGetRootElement / xmlSetGenericErrorFunc).
        Prepend the SDK llvm/lib so lld loads its ABI-matched libxml2.

        Note: ltl2ba itself does NOT depend on libxml2; this is the build
        tool's (lld executable) runtime requirement, not a link dependency
        of the produced binary. Same approach as abr2gbr/1.0.2,
        abseil/20260526, avisynthplus/3.7.5.
        """
        if str(self.settings.os) != "OHOS":
            return ""
        cc = self._get_cc()
        cc_real = os.path.realpath(cc)
        llvm_lib = os.path.join(
            os.path.dirname(os.path.dirname(cc_real)), "lib"
        )
        return llvm_lib if os.path.isdir(llvm_lib) else ""

    def build(self):
        # R33: CC/CFLAGS come from the Conan toolchain environment
        # (conanbuild), never from raw shell variables. The OHOS profile
        # sets tools.build:compiler_executables so the right cross-compiler
        # is used. -O2 keeps the upstream optimisation intent without the
        # strict -ansi mode that can warn on some toolchains; -DNXT enables
        # the X (next) operator, matching the upstream default build.
        # -j1 avoids races on low-resource CI workers.
        # The Makefile lives in the source tree root; build() otherwise
        # runs in build_folder (a build-release/ subdir with no Makefile).
        #
        # The OHOS SDK lld linker itself needs libxml2.so.16 at link time;
        # prepend the SDK llvm/lib (derived from the active compiler) so lld
        # loads its ABI-matched libxml2 instead of a shadowed one. ltl2ba is
        # NOT linked against libxml2 — this is the linker's own runtime env.
        sdk_ld = self._sdk_llvm_libdir()
        ld_env = (
            f'LD_LIBRARY_PATH="{sdk_ld}:$LD_LIBRARY_PATH" ' if sdk_ld else ""
        )
        self.run(
            ld_env
            + 'make CC="${CC:-clang}" '
            'CFLAGS="-O2 -DNXT" '
            '-j1',
            env="conanbuild",
            cwd=self.source_folder,
        )

    def package(self):
        # ltl2ba is a single executable — install into package/bin (R38).
        # The binary is produced in the source tree root by the Makefile.
        copy(
            self,
            "ltl2ba",
            self.source_folder,
            os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
