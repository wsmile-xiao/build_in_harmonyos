#!/usr/bin/env python3
"""Conan recipe for unadf 0.7.11a (ADFlib + unadf CLI) on OHOS aarch64.

Upstream is a hand-written Makefile tree from 2006/2007 (Levy, GPL-2.0+) that
never gained LP64 support. Three portability hazards, all handled without
touching upstream sources by hand:

1. LP64 `long` in the on-disk Amiga structures. `Lib/adf_blk.h` and
   `Lib/adf_str.h` declare every field of `bRootBlock`, `bDirBlock`,
   `bFileHeaderBlock`, ... as `long`, and `adf_env.c:adfEnvInitDefault()`
   aborts at startup unless `sizeof(long)==4`. On aarch64 LP64 that is 8, so
   the tool exits 1 before doing any work. We ship Debian's own upstream
   `64-bit-fixes` patch (from unadf 0.7.11a-5+deb12u1, by Henri Nowotka,
   Debian bug #458129), which rewrites the on-disk fields to `int32_t`/
   `uint32_t` and relaxes the guard to `sizeof(int32_t)!=4`. This is the
   same fix Debian has shipped since 2011, not a locally invented one.

2. `Lib/Generic/adf_nativ.h` and `adf_nativ.c` carry a stray duplicated
   comment terminator, so any modern compiler fails on line 23 with
   "expected identifier or '('", and the seven `#include "defendian.h"`
   sites point at a header that the tarball does not ship at that path.
   Debian's own `source-code-fixes` patch removes the terminator and
   repoints the includes at `Win32/defendian.h`, which does ship and
   defines LITT_ENDIAN=1 for a little-endian host. We apply it verbatim.

3. `Lib/Makefile` hardcodes `CC=gcc` and both Makefiles end with
   `include .depend` (a file whose only content is a single newline). We
   override the toolchain variables on the make command line and pass an empty
   DEPEND= so nothing tries to regenerate the dependency file.

The two Debian patches are applied source-code-fixes first, then 64-bit-fixes:
0002's context lines assume 0001's rewritten #include directives. GNU patch
absorbs the mismatch with fuzz, but conan's apply_conandata_patches() uses
`git apply -p1`, which is strict. The quilt headers were also normalised from
`unadf-0.7.11a.orig/` + `unadf-0.7.11a/` to `a/` + `b/` for the same reason;
the hunk bodies are byte-identical to Debian's.

The library is delivered static-only (R26/R35): the upstream shared target has
no SONAME/versioning machinery, and OHOS ships its own process model.

The package is nonetheless declared package_type="application", because it ships
the unadf CLI in bin/ as well as libadf.a, and package_type is what makes the
packaged bin/ reach the run trait. See the comment on the class attribute.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

DEFENDIAN = "#ifndef LITT_ENDIAN\n#define LITT_ENDIAN 1\n#endif /* LITT_ENDIAN */\n"


class UnadfConan(ConanFile):
    name = "unadf"
    version = "0.7.11a"
    description = "unzip-like extractor for Amiga ADF disk images (ADFlib + unadf CLI)"
    license = "GPL-2.0-or-later"
    homepage = "http://lclevy.free.fr/adflib/unadf.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # "application", not "library": the package ships the unadf CLI alongside
    # libadf.a, and package_type is what makes CppInfo.deduce() propagate
    # bindirs into the run trait. With "library" the explicit
    # `self.cpp_info.bindirs = ["bin"]` in package_info() never reached the run
    # trait, VirtualRunEnv generated an empty `for v in` list, and the
    # consumer test died on "unadf binary not on PATH" even though p/bin/unadf
    # was present and executable. Device-verified 2026-09-29: changing only
    # this line to "application" moved the generated env from
    # `for v in` (empty) to `for v in PATH LD_LIBRARY_PATH DYLD_LIBRARY_PATH`
    # and took the suite from PASS=0 FAIL=1 to PASS=15 FAIL=0. The
    # 33 package_type="application" recipes already in this repo are the same
    # shape, and none of them carries a `shared` option.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # No `shared` option: this package is static-only by construction. The
    # upstream Lib/Makefile shared rule builds libadf.so.0.7.11 with no SONAME
    # or versioning machinery and is deliberately not used (see the module
    # docstring), build() never reads options.shared, and package_id() below
    # already deletes compiler and build_type. Keeping the option was dead
    # weight that also made Conan warn
    # "package_type 'application' is defined, but 'shared' and/or
    # 'header_only' options are present" on every graph computation.
    # Device-verified 2026-09-29: with the option removed, conan create is
    # clean (no WARN) and still reports PASS=15 FAIL=0.

    no_copy_source = True

    exports_sources = "patches/*", "*.txt"

    def export_sources(self):
        # Both halves are required for apply_conandata_patches() to work: this
        # copies the patch files into the exported recipe (build() looks for
        # them next to conandata.yml in the cache), and it is a no-op unless
        # conandata's `patches` is the flat list form.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # conan_data is keyed [package_name/version] -> entry. The leading
        # "unadf/" is the conan reference name, not a literal key.
        # CI rewrites conandata `url` into a [mirror, upstream] list; accept both.
        entry = self.conan_data["sources"][f"{self.name}/{self.version}"]
        candidates = entry["url"]
        if not isinstance(candidates, list):
            candidates = [candidates]
        get(self, **dict(entry, url=candidates[0]), strip_root=True)

    def _toolchain(self):
        """R33: take the toolchain from Conan conf, never from the shell env.

        The profile stores tools.build:compiler_executables as a dict
        ({'c': ..., 'cpp': ...}), so it must be read whole and then keyed —
        reading the per-tool sub-key raises ConanException.
        """
        ce = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict) or {}
        return (ce.get("c") or "clang",
                # The ohos-aarch64 profile only pins 'c' and 'cpp'; there is no
                # 'ar'/'ranlib' key to read, so these fall back to the llvm
                # binutils that ship next to the pinned clang. Keep the "rc"
                # operation the Makefile needs -- see the note in build().
                ce.get("ar") or "llvm-ar",
                ce.get("ranlib") or "llvm-ranlib")

    def build(self):
        cc, ar, ranlib = self._toolchain()

        # Upstream fixes, both taken verbatim from Debian: without the second
        # Lib/Generic/adf_nativ.h does not parse at all, and without the first
        # adfEnvInitDefault() exits 1 on any 64-bit target. Order is 0001 then
        # 0002 by conandata; see the module docstring.
        apply_conandata_patches(self)

        # 2006 sources predate C89 prototypes in some definitions; build as
        # gnu99 and silence the prototype/implicit-decl diagnostics that modern
        # clang promotes. -fcommon keeps the tentative globals in the 2006
        # headers linkable under clang's -fno-common default.
        #
        # Overriding CFLAGS replaces the Makefile's own value wholesale, so the
        # upstream include paths have to be carried over: Lib/Makefile passes
        # -I./Generic -I.. -I., and Demo/Makefile passes -I../Lib. Without them
        # adf_hd.c fails on the very first #include.
        #
        # CFLAGS is passed as a make variable assignment, so its value must be
        # one shell word: self.run() goes through a shell and would otherwise
        # split it into separate argv entries that make reads as invalid
        # options.
        base = "-O2 -fcommon -std=gnu99 -Wno-strict-prototypes"
        lib_cflags = f"{base} -I./Generic -I.. -I."
        demo_cflags = f"{base} -I../Lib"

        # Lib/Makefile declares `AR=ar rc` -- the archive operation is part of
        # the variable, and the rule is `$(AR) $@ $(OBJS)`. Overriding AR with
        # a bare `llvm-ar` therefore drops the operation and llvm-ar treats
        # `libadf.a` as an option string ("error: unknown option f"). The
        # override has to carry the operation too, as ONE make variable
        # assignment -- hence the quotes. Unquoted, make would parse `rc` as
        # a goal and fail with "No rule to make target 'rc'".
        #
        # The recipe also drops -Wall/-Wno-uninitialized/-pedantic from
        # upstream CFLAGS and replaces -ggdb with -O2. The warnings are
        # 2006-era noise under clang 15; the optimisation level is a package
        # decision, and conan controls debug symbols via build_type.
        #
        # Demo/Makefile links with `$(CC) $(CFLAGS) -o $@ unadf.o $(LDFLAGS)`
        # where LDFLAGS=-L../Lib -ladf, and its `unadf` target depends on the
        # `lib` phony rule that recurses into Lib/. Both are already correct
        # upstream, so only the toolchain and CFLAGS need overriding.
        common = f"CC={cc} AR='{ar} rc' RANLIB={ranlib} DEPEND="

        # R9: -j1 only.
        self.run(f"make -C Lib {common} CFLAGS='{lib_cflags}' -j1",
                 cwd=self.source_folder)
        self.run(f"make -C Demo {common} CFLAGS='{demo_cflags}' -j1",
                 cwd=self.source_folder)

    def package(self):
        lib = os.path.join(self.source_folder, "Lib")
        copy(self, "*.h", lib, os.path.join(self.package_folder, "include"))
        copy(self, "*.a", lib, os.path.join(self.package_folder, "lib"))
        copy(self, "unadf", os.path.join(self.source_folder, "Demo"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["adf"]
        self.cpp_info.bindirs = ["bin"]

        # R38/PF8: CLI metadata lives at the software level
        # (archives/u/unadf/commands.json), not per version.

    def package_id(self):
        # Static archive of a fixed C toolchain: no build-type component.
        del self.info.settings.compiler
        del self.info.settings.build_type
