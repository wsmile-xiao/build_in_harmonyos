#!/usr/bin/env python3
"""Conan recipe — mlv-smile 1.47 (SMILE v1.47, structured motif extraction).

Academic autotools-free package: the top Makefile recurses into three
sub-Makefiles (P_BLOCS, P_BLOCS+DELTA, SigStat), each hardcoding CC=gcc.
OHOS has no gcc, so the compiler is overridden on the make command line
(M18 pool mechanism: command-line variable assignment beats the baked
value and propagates to sub-makes through MAKEFLAGS).  There is no
configure, no install target and no upstream test suite; package() lays
out the five built tools plus the Lanceur example data used by the
consumer test.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout

SUBMAKES = ("P_BLOCS", "P_BLOCS+DELTA", "SigStat")
# subtree -> translation unit holding the single ALPHA_CARD definition
SUBMAKES_WITH_DEF = (
    ("P_BLOCS", "src/global_fonctions.c"),
    ("P_BLOCS+DELTA", "src/global_variables.c"),
    ("SigStat/grep+", "src/global_variables.c"),
)
TOOLS = ("x-smile", "x-smile_delta", "e-smile_shuffling", "e-smile_against",
         "grep+")


class MlvSmileConan(ConanFile):
    name = "mlv-smile"
    version = "1.47"
    description = (
        "SMILE: exact extraction of simple/structured models in sequences "
        "with statistical significance evaluation"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/resurrecting-open-source-projects/smile"
    url = ""  # CI fills this
    topics = ("bioinformatics", "motif-discovery", "sequences", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mlv-smile not validated for {self.settings.os}"
            )

    def export_sources(self):
        # No upstream patches exist; conandata.yml declares none.  The
        # method is kept for the G1 recipe-completeness gate.
        pass

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)  # no-op: conandata declares no patches
        # E491 (clang -fno-common): every subtree's include/define.h
        # tentatively defines "int ALPHA_CARD;" so each translation unit
        # including it becomes a definition; ld.lld then fails with
        # duplicate symbol.  Remedy per E491: normalize the header to a
        # single extern declaration and keep exactly one definition per
        # subtree.  Deliberately NOT -fcommon (E491 forbid_1).  All steps
        # are idempotent so repeated builds converge to the same state.
        src = self.source_folder
        pat = re.compile(r"^[ \t]*(?:extern[ \t]+)*int[ \t]+ALPHA_CARD;[ \t]*$", re.M)
        for sub, defc in SUBMAKES_WITH_DEF:
            dh = os.path.join(src, sub, "include", "define.h")
            with open(dh) as f:
                content = f.read()
            if not pat.search(content):
                raise ConanInvalidConfiguration(
                    "ALPHA_CARD tentative definition not found in " + dh)
            content = pat.sub("extern int ALPHA_CARD;", content, count=1)
            with open(dh, "w") as f:
                f.write(content)

            dc = os.path.join(src, sub, defc)
            with open(dc) as f:
                dlines = f.readlines()
            changed = False
            out = []
            for line in dlines:
                if pat.match(line):
                    changed = True   # drop stray definitions from earlier runs
                    continue
                out.append(line)
            if not changed:
                last_inc = max(i for i, l in enumerate(out)
                               if l.startswith("#include"))
                out.insert(last_inc + 1, "int ALPHA_CARD;" + chr(10))
                changed = True
            # a stray definition may exist in ANOTHER .c of the subtree:
            # leave removal to the fresh-extract guarantee (conan remove
            # before build); the designated defc now holds the definition.
            with open(dc, "w") as f:
                f.writelines(out)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = (compilers or {}).get("c") or "clang"
        # M18: CC=gcc is baked into every sub-Makefile; a command-line
        # assignment overrides it and reaches the recursive sub-makes via
        # MAKEFLAGS.  No gcc exists on OHOS, so without this the very first
        # compile dies on "gcc: No such file or directory".
        # P_BLOCS / P_BLOCS+DELTA build independently; SigStat's upstream
        # `all` target is ORDER-DEPENDENT (its grep+ rule populates obj
        # trees that the e-smile link rules consume) and is not -j-safe —
        # parallel make linked e-smile_shuffling before grep+/Spell/obj/
        # model.o existed (measured).  SigStat therefore builds serially.
        self.run(f'make -C "P_BLOCS" -j2 CC="{cc}"', cwd=src)
        self.run(f'make -C "P_BLOCS+DELTA" -j2 CC="{cc}"', cwd=src)
        self.run(f'make -C "SigStat" CC="{cc}"', cwd=src)

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for sub in SUBMAKES:
            copy(self, "*", src=os.path.join(src, sub, "bin"), dst=bindir,
                 keep_path=False)
        # Lanceur example data: the consumer test drives the real tool with
        # the annotated param_example; shipping it keeps that reproducible.
        copy(self, "*", src=os.path.join(src, "Lanceur"),
             dst=os.path.join(self.package_folder, "res", "examples"),
             keep_path=False)
        for license_file in ("COPYING", "COPYING.gpl", "COPYING.lgpl"):
            copy(self, license_file, src=src,
                 dst=os.path.join(self.package_folder, "licenses"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res/examples"]
