#!/usr/bin/env python3
"""Conan recipe for kazlib 1.21 — raw Makefile build (upstream Makefile.gcc).

kazlib is a collection of self-contained ANSI C data structures (dictionary,
hash table, doubly linked list, exceptions, expression side-effect analysis)
by Kaz Kylheku. Upstream ships no configure/cmake: a hand-written Makefile.gcc
builds the static and shared libraries; its self-check driver rules pass
headers as link inputs (GCC-tolerant, clang-rejected), so this recipe compiles
those five drivers from the same sources with the same KAZLIB_TEST_MAIN switch.

No source patches are needed: the toolchain is passed to make through the
environment (Makefile.gcc honours `CC ?=`-style defaults and layers
target-specific CFLAGS for the test mains on top of them).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class LibkazConan(ConanFile):
    name = "libkaz"
    version = "1.21"
    description = "Kazlib ANSI C data structures: dictionary, hash table, list, exceptions"
    license = "BSD-3-Clause"
    homepage = "https://savannah.nongnu.org/projects/kazlib/"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # kazlib is self-contained ANSI C: it uses only libc.
        pass

    def validate(self):
        # R32: OHOS must be accepted alongside Linux.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("kazlib supports Linux/OHOS only")

    def layout(self):
        basic_layout(self)
        # Makefile.gcc is an in-source build (objects/libs land next to sources).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain(self):
        """R33: tool names come from the Conan conf, never from shell env."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        bindir = os.path.dirname(cc)

        def tool(basename, fallback):
            candidate = os.path.join(bindir, basename) if bindir else basename
            return candidate if not bindir or os.path.exists(candidate) else fallback

        return cc, cxx, tool("llvm-ar", "ar"), tool("llvm-ranlib", "ranlib")

    def build(self):
        apply_conandata_patches(self)
        cc, cxx, ar, ranlib = self._toolchain()
        src = self.source_folder

        # The self-check drivers are interactive REPLs reading command scripts
        # from stdin. Feed real operations (append/lookup/delete/dump plus the
        # 1.21 strict-bound lookups) so the runs exercise the library instead of
        # exiting trivially on EOF. The driver shells read them via redirection.
        save(self, os.path.join(src, "tlist.input"),
             "a alpha\na beta\na gamma\nl beta\ns\nt\nd alpha\nc\nq\n")
        save(self, os.path.join(src, "tdict.input"),
             "a 1 one\na 2 two\na 3 three\nl 2\n< 2\n> 2\nc\nt\nd 1\nc\nq\n")
        save(self, os.path.join(src, "thash.input"),
             "a k1 v1\na k2 v2\na k3 v3\nl k2\nn\nc\nt\nd k1\nc\nq\n")
        save(self, os.path.join(src, "teh.input"), "y\n")

        # Makefile.gcc layers target-specific CFLAGS on top of its `?=` defaults
        # (-DKAZLIB_TEST_MAIN for the test mains), so the toolchain must travel
        # through the environment: command-line variable assignments would
        # suppress those target-specific additions. -fPIC is required because
        # the shared library is linked by whole-archive from the static one.
        # CXXFLAGS is also set explicitly: a CI worker's conan buildenv exports
        # its own CXXFLAGS, which would shadow the Makefile's `?=` derivation
        # and leave the C++ test without upstream flags or include path.
        cflags = "-fPIC -Wall -W -Wmissing-prototypes -ansi -O2 -DNDEBUG"
        cxxflags = "-fPIC -Wall -W -ansi -O2 -DNDEBUG"
        toolenv = (
            f'CC="{cc}" CXX="{cxx}" AR="{ar}" RANLIB="{ranlib}" '
            f'CFLAGS="{cflags}" CXXFLAGS="{cxxflags}"')
        self.run(f'{toolenv} make -f Makefile.gcc libkaz.a -j1', cwd=src)

        # Upstream's OBJS omits the list module (intended for direct source
        # inclusion), so a plain -lkaz would miss the list_* API. Compile
        # list.o with the library flags and add it to the archive before the
        # shared library is whole-archive-linked from it, so the installed
        # library covers all five modules. No source file is modified.
        self.run(f'"{cc}" {cflags} -c list.c -o list.o', cwd=src)
        self.run(f'"{ar}" rcs libkaz.a list.o', cwd=src)
        self.run(f'{toolenv} make -f Makefile.gcc libkaz.so.1.0.0 -j1', cwd=src)

        # Upstream's `project` target also builds the five self-check drivers,
        # but its rules pass header files as link inputs (`tdict: dict.c
        # dict.h` -> `$(CC) -o tdict dict.c dict.h`), which GCC tolerates and
        # clang rejects ("cannot specify -o when generating multiple output
        # files"). Compile each driver from its module with the exact switch
        # the Makefile would add (CFLAGS + -DKAZLIB_TEST_MAIN); tsfx links the
        # except.o/hash.o objects produced for the library, as upstream does.
        for prog, module in (("tlist", "list.c"), ("tdict", "dict.c"),
                             ("thash", "hash.c"), ("teh", "except.c")):
            self.run(f'"{cc}" {cflags} -DKAZLIB_TEST_MAIN -o {prog} {module}', cwd=src)
        self.run(f'"{cc}" {cflags} -DKAZLIB_TEST_MAIN -o tsfx sfx.c except.o hash.o', cwd=src)

        # Same story for the C++ wrapper test: upstream compiles tests/dict-1.cc
        # through the builtin %.o:%.cc rule, which honors CXXFLAGS only — the
        # Makefile's include-path addition targets CFLAGS and never reaches it.
        # Compile it explicitly with the derived upstream flags and the same
        # link line the Makefile uses (tests/dict-1.o + dict.o).
        self.run(f'"{cxx}" {cxxflags} -I. -c tests/dict-1.cc -o tests/dict-1.o', cwd=src)
        self.run(f'"{cxx}" -o tests/dict-1 tests/dict-1.o dict.o', cwd=src)

        self._run_selfchecks()

    def _selfcheck(self, prog, stdin_file, expect_markers, expect_abort=False,
                   forbidden=None):
        """Run one upstream self-check driver and assert on its transcript.

        The REPL drivers print failure text (but stay exit 0) when an operation
        fails, so the exit code alone is not enough: fail on any failure marker
        in the transcript and require the expected content markers. `teh` is the
        upstream-designed exception: it ends in the deliberate unhandled-throw
        path, i.e. SIGABRT (shell status 134). On OHOS the piped stdout buffer
        is discarded by abort(), so teh's assertions rely on the explicitly
        flushed prompt line and on the unhandled-exception identity: seeing
        ("exception in main", group=99) proves both nested catch frames handled
        and rethrew the thrown {1,1} exception, or the unhandled report would
        name ("nasty exception", group=1) instead.
        """
        patterns = forbidden or (
            " *'what?'*|*'failed'*|*'warning'*|*'out of memory'*|*'allocation failure'*)")
        expected = "134" if expect_abort else "0"
        checks = [
            f'out=$(./{prog} < {stdin_file} 2>&1)',
            'rc=$?',
            'echo "$out"',
            f'test "$rc" -eq {expected} || '
            f'{{ echo "{prog}: exit $rc (expected {expected})"; exit 1; }}',
            f'case "$out" in{patterns} echo "{prog}: failure marker in transcript"; exit 1;; esac',
        ]
        for marker in expect_markers:
            checks.append(
                f'case "$out" in *\'{marker}\'*) : ;; *) '
                f'echo "{prog}: missing expected marker \'{marker}\'"; exit 1;; esac')
        self.run("; ".join(checks), cwd=self.source_folder)

    def _run_selfchecks(self):
        self._selfcheck("tlist", "tlist.input", ["gamma", "beta"])
        self._selfcheck("tdict", "tdict.input", ["one", "three"])
        self._selfcheck("thash", "thash.input", ["v1", "v2", "v3"])
        # teh: the abort discards buffered stdout on OHOS, so assert only the
        # fflushed prompt, the unhandled-throw identity (see _selfcheck), and
        # the SIGABRT status; skip the standard forbidden-marker scan because
        # the upstream message text is outside its scope here.
        self._selfcheck(
            "teh", "teh.input",
            ["throw exception? ", "Unhandled exception", "group=99, code=99"],
            expect_abort=True, forbidden=" *'failed'*)")
        self.run('./tsfx "x" "x + 1" "x = 1"', cwd=self.source_folder)
        self.run("./tests/dict-1", cwd=self.source_folder)
        print("kazlib upstream self-checks: 6/6 drivers exercised (tlist tdict thash teh tsfx tests/dict-1)")

    def package(self):
        src = self.source_folder
        copy(self, "*.h", src, os.path.join(self.package_folder, "include", "kazlib"))
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(self, "libkaz.so.1.0.0", src, libdir)
            # HMDFS does not overwrite existing links: remove before creating.
            for name in ("libkaz.so.1", "libkaz.so"):
                link = os.path.join(libdir, name)
                if os.path.islink(link) or os.path.exists(link):
                    os.remove(link)
                os.symlink("libkaz.so.1.0.0", link)
        else:
            copy(self, "libkaz.a", src, libdir)

    def package_info(self):
        # Headers install under include/kazlib (same layout as upstream's
        # `install` target); consumers include <kazlib/dict.h> etc.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["kaz"]
