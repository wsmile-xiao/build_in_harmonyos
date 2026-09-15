#!/usr/bin/env python3
"""Conan recipe — wuffs 0.4.0-alpha.10.

Wuffs is a programming language plus a standard library written in that
language (image/compression/JSON codecs, hashers) whose distributable form is
generated C. "Wuffs the Library" ships as a *single file C library* (stb-style
header file library) under release/c/, and upstream's releases are files in
that directory, not separate archives.

This package therefore installs exactly one file:

    release/c/wuffs-v0.4.c   ->   include/wuffs/wuffs-v0.4.c

It acts as a header, or as a translation unit when the consumer defines
WUFFS_IMPLEMENTATION before including/compiling it. The unversioned
release/c/wuffs-unsupported-snapshot.c is deliberately NOT installed: upstream
documents it as unsupported (its WUFFS_VERSION is 0 because it is only meant to
be driven together with `wuffs test`/`wuffs genlib` generated code), whereas
the versioned file carries WUFFS_VERSION = 0x000040000 and is what consumers are
told to copy into their projects.

Build strategy: upstream has no configure/make/build-system step for the
library itself (BUILD.md: "There's no build step"); the repository's coherence
script is build-all.sh. This recipe ports the parts of build-all.sh that do not
need the Go toolchain (which is unavailable in the OHOS CI image) and add
nothing else:

  1. the four "compiles cleanly" checks on the shipped file — C99 and C++11,
     with and without WUFFS_IMPLEMENTATION, using upstream's own warning set
     from build-all.sh;
  2. every upstream C test program under test/c/std/ (30 programs, each an
     independent single-translation-unit test binary), compiled exactly the way
     up-cmd `wuffs-c test` compiles them (-std=c99 -Wall -Werror), executed,
     and required to print its "PASS (N tests)" line with N > 0.

The 30 test programs are the part of the upstream suite that runs without the
Go toolchain (`wuffs test` transpiles and checks Wuffs sources with it). They
are patched (see conandata.yml) to include the versioned wuffs-v0.4.c instead of
the development snapshot, so the tests exercise the very file this package
installs — without that, the tests would validate release/c files nobody
installs, and the version check inside every decoder's initialize call
(WUFFS_VERSION) would not match.
"""

import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# Upstream build-all.sh, verbatim. Kept in one place so the four coherence
# checks below cannot drift from each other.
# C++ note: -Wno-c99-extensions is added on top for the C++ compilations.
# Wuffs' generated C uses C99 compound literals in its AArch64/NEON code paths;
# under -Wpedantic those are 8 hard diagnostics (the release file's own
# `#pragma GCC diagnostic ignored ...` block exists precisely because "Wuffs' C
# code is generated automatically" and these warnings' costs outweigh their
# benefits). Turning that single warning off keeps -Werror meaningful instead of
# weakening the whole check.
_WARNING_FLAGS = (
    "-Wall -Werror -Wpedantic -Wcast-qual -Wcast-align -Wpointer-arith "
    "-Wfloat-equal -Wundef -Wvla -Wconversion -Wshadow -Wredundant-decls "
    "-Wunused-const-variable"
)
_C_WARNING_FLAGS = _WARNING_FLAGS + " -Wstrict-prototypes -Wold-style-definition"
_CXX_WARNING_FLAGS = _WARNING_FLAGS + " -Wno-c99-extensions"

# Same flags `wuffs-c test` uses for the C test programs (cmd/wuffs-c/test.go).
_TEST_FLAGS = "-std=c99 -Wall -Werror"


class WuffsConan(ConanFile):
    name = "wuffs"
    version = "0.4.0-alpha.10"
    description = (
        "Wuffs the Library: a memory-safe standard library of image, "
        "compression and JSON codecs plus hashers, distributed as a single "
        "file C library"
    )
    license = "Apache-2.0 OR MIT"
    homepage = "https://github.com/google/wuffs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = (
        "image", "codec", "png", "gif", "jpeg", "deflate", "gzip", "zlib",
        "crc32", "adler32", "header-only", "single-file",
    )

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # No build system: keep the source tree as-is and put the generated test
        # binaries in the build folder instead of inside the source tree.
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _single_c_file(self):
        """Return the basename of the versioned single-file release to ship.

        release/c/wuffs-vMAJOR.MINOR.c is the versioned artifact; for
        0.4.0-alpha.10 that is wuffs-v0.4.c.
        """
        parts = str(self.version).split(".")
        if len(parts) < 2:
            raise ConanException(
                "cannot derive the release/c/wuffs-vMAJOR.MINOR.c name from "
                "version '%s'" % self.version
            )
        return "wuffs-v%s.%s.c" % (parts[0], parts[1])

    def _single_c_path(self):
        name = self._single_c_file()
        path = os.path.join(self.source_folder, "release", "c", name)
        if not os.path.isfile(path):
            available = []
            rel_c = os.path.join(self.source_folder, "release", "c")
            if os.path.isdir(rel_c):
                available = sorted(os.listdir(rel_c))
            raise ConanException(
                "expected upstream versioned single-file release %r under "
                "release/c/, found: %s" % (name, available)
            )
        return name, path

    def _compilers(self):
        # R33: take the toolchain from Conan conf, never from ambient shell
        # variables. tools.build:compiler_executables is a dict conf and Conan
        # 2.x conf.get has no dotted subkey access, so fetch the dict first.
        executables = self.conf.get("tools.build:compiler_executables") or {}
        return executables.get("c", "clang"), executables.get("cpp", "clang++")

    def build(self):
        apply_conandata_patches(self)

        single_name, single_path = self._single_c_path()
        cc, cxx = self._compilers()
        bindir = os.path.join(self.build_folder, "test-bin")
        os.makedirs(bindir, exist_ok=True)
        rel = os.path.join("release", "c", single_name)

        # (1) build-all.sh coherence checks: the shipped file must compile
        #     warning-clean as a header and as an implementation, in C99 and in
        #     C++11.
        checks = (
            ("header-only (C99)", cc, "-std=c99 -Wc++-compat", _C_WARNING_FLAGS, False),
            ("implementation (C99)", cc, "-std=c99 -Wc++-compat", _C_WARNING_FLAGS, True),
            ("header-only (C++11)", cxx, "-std=c++11 -x c++", _CXX_WARNING_FLAGS, False),
            ("implementation (C++11)", cxx, "-std=c++11 -x c++", _CXX_WARNING_FLAGS, True),
        )
        for label, compiler, std_flags, warning_flags, implementation in checks:
            obj = os.path.join(bindir, re.sub(r"[^A-Za-z0-9]+", "-", label) + ".o")
            define = " -DWUFFS_IMPLEMENTATION" if implementation else ""
            self.run(
                '{compiler} -c {warnings}{define} {std_flags} "{src}" -o "{obj}"'.format(
                    compiler=compiler,
                    warnings=warning_flags,
                    define=define,
                    std_flags=std_flags,
                    src=rel,
                    obj=obj,
                ),
                cwd=self.source_folder,
            )
            self.output.info("coherence check OK: %s" % label)

        # (2) upstream C test suite: 30 independent single-translation-unit
        #     programs under test/c/std/, compiled and run the way `wuffs-c
        #     test` does it. Each program chdir()s to the Wuffs root itself, so
        #     it is launched from the source folder.
        std_dir = os.path.join(self.source_folder, "test", "c", "std")
        if not os.path.isdir(std_dir):
            raise ConanException(
                "upstream C test directory test/c/std is missing from the source tree"
            )
        sources = sorted(f for f in os.listdir(std_dir) if f.endswith(".c"))
        if not sources:
            raise ConanException("no upstream C test programs found in test/c/std")
        if len(sources) != 30:
            # Informational only: upstream may add/remove test programs in a
            # future release. The count is reported so a silent drop is visible.
            self.output.warning(
                "expected 30 upstream C test programs in test/c/std, found %d"
                % len(sources)
            )

        total_cases = 0
        failures = []
        for src in sources:
            name = src[: -len(".c")]
            exe = os.path.join(bindir, name)
            self.run(
                '{cc} {flags} "{src}" -o "{exe}"'.format(
                    cc=cc,
                    flags=_TEST_FLAGS,
                    src=os.path.join("test", "c", "std", src),
                    exe=exe,
                ),
                cwd=self.source_folder,
            )
            # self.run() does not hand back the child's stdout, and the test
            # programs report through it. Capture it in a file and read it.
            out_file = os.path.join(bindir, name + ".out")
            self.run('"%s" > "%s" 2>&1' % (exe, out_file),
                     cwd=self.source_folder)
            with open(out_file, encoding="utf-8", errors="replace") as fh:
                out = fh.read()
            match = re.search(r"PASS \((\d+) tests?\)", out)
            if not match:
                failures.append(name)
                self.output.error(
                    "upstream C test %s printed no 'PASS (N tests)' line; "
                    "output was:\n%s" % (name, out.strip())
                )
                continue
            cases = int(match.group(1))
            if cases <= 0:
                failures.append(name)
                self.output.error(
                    "upstream C test %s reported zero executed test cases" % name
                )
                continue
            total_cases += cases

        if failures:
            raise ConanException(
                "upstream C tests failed to run: %s" % ", ".join(failures)
            )
        self.output.info(
            "upstream C tests: %d programs, %d test cases, all PASS"
            % (len(sources), total_cases)
        )

        # (3) build-all.sh's end-to-end example checks. build-all.sh builds the
        #     example programs and compares their output against upstream's
        #     frozen regression data (test/nia-checksums-of-data.txt,
        #     test/mzcat-checksums-of-data.txt).
        #     SCOPE: these example programs #include the *unversioned snapshot*
        #     (release/c/wuffs-unsupported-snapshot.c) - the portability patches
        #     only repoint test/c/std/*.c - exactly as upstream build-all.sh runs
        #     them. So this block is an upstream-parity check of the recipe's
        #     compile/run pipeline, NOT evidence about the shipped file. The
        #     delivered artifact (release/c/wuffs-v0.4.c) is what the 30 patched
        #     test/c/std programs and test_package/ exercise.
        self._run_example_golden_checks(cc, cxx, bindir)

    def _run_example_golden_checks(self, cc, cxx, bindir):
        # Upstream build-example.sh's own default flags.
        cflags = ("-O3 -fdata-sections -ffunction-sections -Wall "
                  "-Wl,--gc-sections")
        cxxflags = cflags + " -fno-rtti -fno-exceptions"

        examples = (
            ("crc32", cxx, cxxflags),
            ("jsonptr", cxx, cxxflags),
            ("convert-to-nia", cc, cflags),
            ("mzcat", cc, cflags),
        )
        binaries = {}
        for name, compiler, flags in examples:
            exe = os.path.join(bindir, "example-" + name)
            pattern = "example/%s/*.cc" % name if compiler == cxx else "example/%s/*.c" % name
            self.run(
                '{compiler} {flags} {pattern} -o "{exe}"'.format(
                    compiler=compiler, flags=flags, pattern=pattern, exe=exe
                ),
                cwd=self.source_folder,
            )
            if not os.path.isfile(exe):
                raise ConanException("example program %s did not build" % name)
            binaries[name] = exe

        crc32_exe = binaries["crc32"]

        def probe(exe, extra_args, stdin_path):
            """Run an example with a file on stdin; discard its stderr.

            Upstream's print-*-checksums.sh scripts send stderr to /dev/null
            because the tools legitimately print diagnostics ("unsupported file
            format", "truncated input", ...) for the test data that is not an
            image/compressed file.
            """
            with open(os.path.join(self.source_folder, stdin_path), "rb") as fh:
                proc = subprocess.run(
                    [exe] + list(extra_args),
                    cwd=self.source_folder,
                    stdin=fh,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
            return proc.stdout.decode("utf-8", "replace").strip()

        # (3a) build-all.sh: "Running example-crc32".
        have = probe(crc32_exe, [], "test/data/json-things.formatted.json")
        if have != "cdcc7e35":
            raise ConanException(
                "example-crc32 on test/data/json-things.formatted.json: have "
                "%r, want 'cdcc7e35'" % have
            )

        # (3b) build-all.sh: "Running example-jsonptr", piped into example-crc32.
        with open(
            os.path.join(self.source_folder, "test/data/json-things.unformatted.json"),
            "rb",
        ) as fh:
            jsonptr = subprocess.run(
                [binaries["jsonptr"]], cwd=self.source_folder, stdin=fh,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
        piped = subprocess.run(
            [crc32_exe], cwd=self.source_folder, input=jsonptr.stdout,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        ).stdout.decode().strip()
        if piped != "cdcc7e35":
            raise ConanException(
                "example-jsonptr | example-crc32 on json-things.unformatted.json:"
                " have %r, want 'cdcc7e35'" % piped
            )

        # (3c)/(3d) build-all.sh: print-nia-checksums.sh and
        #     print-mzcat-checksums.sh, diffed against the frozen files. The
        #     scripts walk test/data, skip entries whose digest is "BAD
        #     00000000" and print "<crc> <path>", ordered with LANG=C sort.
        data_root = os.path.join(self.source_folder, "test", "data")
        paths = []
        for dirpath, _dirnames, filenames in os.walk(data_root):
            for filename in filenames:
                full = os.path.join(dirpath, filename)
                paths.append(os.path.relpath(full, self.source_folder))
        paths.sort(key=lambda p: p.encode("utf-8"))

        for exe_name, script_name, golden_rel in (
            ("convert-to-nia", "nia", "test/nia-checksums-of-data.txt"),
            ("mzcat", "mzcat", "test/mzcat-checksums-of-data.txt"),
        ):
            exe = binaries[exe_name]
            lines = ["# Generated by script/print-%s-checksums.sh" % script_name]
            for rel in paths:
                digest = probe(exe, ["--output-crc32-digest"], rel)
                if digest != "BAD 00000000":
                    lines.append("%s %s" % (digest, rel))
            with open(os.path.join(self.source_folder, golden_rel), encoding="utf-8") as fh:
                want = fh.read().splitlines()
            if lines != want:
                first = next(
                    (i for i, (a, b) in enumerate(zip(lines, want)) if a != b),
                    min(len(lines), len(want)),
                )
                raise ConanException(
                    "%s regression data mismatch: have %d lines, want %d, first "
                    "difference at line %d (have %r, want %r)"
                    % (golden_rel, len(lines), len(want), first + 1,
                       lines[first:first + 1], want[first:first + 1])
                )
            self.output.info(
                "golden regression OK: %s (%d entries)" % (golden_rel, len(want) - 1)
            )

    def package(self):
        single_name, _ = self._single_c_path()
        copy(
            self,
            single_name,
            src=os.path.join(self.source_folder, "release", "c"),
            dst=os.path.join(self.package_folder, "include", "wuffs"),
        )
        for license_name in ("LICENSE", "LICENSE-APACHE", "LICENSE-MIT"):
            copy(
                self,
                license_name,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
            )

    def package_info(self):
        # The shipped file is a .c file used as a header; there is nothing to
        # link, so libdirs/bindirs are empty on purpose (keeps L0k/R38 quiet:
        # this is not a CLI tool).
        self.cpp_info.set_property("cmake_file_name", "wuffs")
        self.cpp_info.set_property("cmake_target_name", "wuffs::wuffs")
        self.cpp_info.set_property("pkg_config_name", "wuffs")
        # code-style §4 asks for cpp_info.libs; this package has no linkable
        # target at all (the shipped artifact is a .c file used as a header),
        # so it is declared empty explicitly rather than left unset.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
