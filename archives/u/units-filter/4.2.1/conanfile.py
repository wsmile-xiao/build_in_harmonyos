#!/usr/bin/env python3
"""Conan recipe for units-filter 4.2.1 — physical-quantity expression parser.

Upstream: https://salsa.debian.org/georgesk/units-filter (Debian science
package "units-filter", orig tarball units-filter_4.2.1.orig.tar.xz).
A standalone filter written in C++/flex/bison: it reads strings like
"1.5e3 nN.m.s^-1" on stdin and prints the value in SI units followed by
the physical dimension vector, e.g. "1.5e-06   2   1  -3   0 ...".

Build: plain Makefiles (top Makefile drives docs via sphinx + the gui/
subdirectory; only src/ is built here). src/Makefile compiles
uniteslex.cc (flex), unitesparser.cc (bison), decimal.o (gmpxx) and links
the `units-filter` binary.

OHOS adaptations (vendored sources + in-recipe Makefile edit):
  * Vendored flex/bison outputs (vendored/src/ + in-recipe Makefile edit):
    src/uniteslex.cc (flex 2.6.4), src/unitesparser.cc (bison 3.8.2) and
    src/FlexLexer.h (upstream flex 2.6.4 header, byte-identical) are copied
    from the recipe vendored/ dir in build() (byte-exact copy, so the
    latin-1 bytes in upstream comments never pass through conan's UTF-8
    patch reader), and the src/Makefile flex/bison recipes are neutralized
    in Python (line-based, whitespace-tolerant) so device builds never
    invoke flex/bison. This removes the flex/bison/m4 tool chain entirely:
    ohpcd hosts no m4 recipe, so any m4 edge resolves to conancenter and
    its configure re-exec dies on the profile's
    CONFIG_SHELL=/data/service/hnp/bin/bash (inaccessible).
  * RECODE_SUPPORT is forced empty: upstream enables librecode only when
    /etc/issue contains "Debian"; HarmonyOS has no librecode, and the
    non-Debian branch links just -lm -lgmp, which is what OHOS uses.
  * LIBS is extended with -lgmpxx: decimal.cc uses gmpxx (mpz_class) and
    the upstream LIBS line only lists -lgmp.
  * CC/CXX are resolved with an existence check (conf absolute path only
    if executable, otherwise PATH fallback), not the Makefile's hardcoded
    gcc/g++ defaults.
  * Upstream tests (src/units-test: cat test.1..4 | perl units-test.pl,
    77 cases) run in build() and emit HMBS_UPSTREAM_TEST_RESULT with
    counts parsed from the deterministic OK/***ERREUR*** log lines.
"""

import glob
import json
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


# Upstream test inventory (audited from units-filter_4.2.1.orig.tar.xz):
# src/test.1 = 49 cases, src/test.2 = 11, src/test.3 = 5, src/test.4 = 12.
# Counting rule mirrors src/units-test.pl: non-empty lines form pairs
# (input, expected), except "options=..." lines which set flags for the
# following pair instead of being a case themselves.
UPSTREAM_TEST_DISCOVERED = 77
UPSTREAM_TEST_FRAMEWORK = "make"
UPSTREAM_TEST_COMMAND = "sh units-test (cat test.1 test.2 test.3 test.4 | perl units-test.pl)"


class UnitsFilterConan(ConanFile):
    name = "units-filter"
    version = "4.2.1"
    description = ("Parser for expressions concerning physical values: "
                   "converts quantities like '1.5e3 nN.m.s^-1' to SI "
                   "units with their physical dimension vector")
    license = "GPL-3.0-or-later"
    homepage = "https://salsa.debian.org/georgesk/units-filter"
    url = ""
    topics = ("units", "physics", "parser", "flex", "bison", "ohos")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Byte-exact vendored sources (may contain latin-1 bytes, so they
        # travel via export/copy instead of a conandata patch).
        copy(self, "vendored/*", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "units-filter supports Linux and OHOS only, got %s" % self.settings.os
            )

    def requirements(self):
        # decimal.cc includes <gmpxx.h> (mpz_class); the gmp recipe builds
        # with --enable-cxx so both libgmp and libgmpxx are available (R36).
        self.requires("gmp/6.3.0.1")

    def build_requirements(self):
        # flex/bison outputs are vendored (see docstring);
        # only perl is needed, to run the upstream units-test.pl harness.
        # (flex/bison tool_requires are deliberately absent: ohpcd hosts no
        # m4 recipe, so any flex/bison edge that builds from source pulls
        # conancenter m4 whose configure re-exec fails on the profile's
        # CONFIG_SHELL=/data/service/hnp/bin/bash, twice observed.)
        self.tool_requires("perl/5.42.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _gmp_flags(self):
        dep = self.dependencies["gmp"]
        root = dep.package_folder
        incs = []
        libdirs = []
        for d in dep.cpp_info.includedirs:
            full = d if os.path.isabs(d) else os.path.join(root, d)
            if os.path.isdir(full):
                incs.append(full)
        for d in dep.cpp_info.libdirs:
            full = d if os.path.isabs(d) else os.path.join(root, d)
            if os.path.isdir(full):
                libdirs.append(full)
        return incs, libdirs

    def _resolve_tool(self, name, fallback):
        path = shutil.which(name)
        if path:
            return path
        return os.environ.get("HMBS_" + name.upper(), fallback)

    def _resolve_compiler(self, kind, fallbacks):
        # Only trust conf absolute paths when the file actually exists;
        # the profile may point at /data/service/hnp/bin/clang++ which is
        # absent on the device (Error 127). Fall back through PATH so a
        # real compiler is always used; fail loudly if none is found.
        conf = self.conf.get("tools.build:compiler_executables", default={})
        cand = conf.get(kind)
        if cand:
            if os.path.isabs(cand):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
            else:
                found = shutil.which(cand)
                if found:
                    return found
        env = os.environ.get("CC" if kind == "c" else "CXX")
        if env:
            first = env.split()[0]
            if os.path.isabs(first):
                if os.path.isfile(first):
                    return env
            else:
                found = shutil.which(first)
                if found:
                    return env
        for name in fallbacks:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                return found
        if cand:
            return cand
        raise ConanException("no %s compiler found (tried %s)" % (kind, fallbacks))

    def _conan_perl(self):
        for dep in self.dependencies.build.values():
            if dep.ref.name == "perl" and dep.package_folder:
                cand = os.path.join(dep.package_folder, "bin", "perl")
                if os.path.isfile(cand):
                    return cand
        return shutil.which("perl") or "/data/service/hnp/bin/perl"

    def build(self):
        apply_conandata_patches(self)
        # Lay the vendored flex/bison outputs into the source tree
        # (byte-exact; the Makefile recipes for them are neutralized below).
        copy(self, "*", src=os.path.join(self.export_sources_folder, "vendored"),
             dst=self.source_folder)
        src_dir = os.path.join(self.source_folder, "src")
        if not os.path.isfile(os.path.join(src_dir, "Makefile")):
            raise ConanException("src/Makefile missing from source tree")
        self._neutralize_makefile(os.path.join(src_dir, "Makefile"))

        make = os.environ.get("HMBS_MAKE") or shutil.which("make") or "make"
        cc = self._resolve_compiler("c", ["cc", "clang", "gcc"])
        cxx = self._resolve_compiler("cpp", ["c++", "clang++", "g++"])
        self.output.info("resolved compilers: CC=%s CXX=%s" % (cc, cxx))

        incs, libdirs = self._gmp_flags()
        self.output.info("gmp incs=%r libdirs=%r" % (incs, libdirs))
        if not incs:
            dep = self.dependencies["gmp"]
            try:
                entries = sorted(os.listdir(dep.package_folder))
            except OSError:
                entries = ["<unlistable>"]
            raise ConanException(
                "gmp headers not found (incs empty, package_folder=%s entries=%r)" % (dep.package_folder, entries[:30]))
        cxxflags = "-g -Wall"
        cxxflags += " " + " ".join("-I%s" % d for d in incs)
        # <FlexLexer.h> is vendored into src/ (see docstring); the Makefile
        # compiles with cwd=src/ but angle-includes don't search cwd, so add
        # an explicit -I for it (same mechanism as the gmp -I above).
        cxxflags += " -I%s" % src_dir
        # Upstream LIBS is "-lm -lgmp" (non-Debian branch, no librecode on
        # OHOS); -lgmpxx is added because decimal.cc uses gmpxx (mpz_class).
        # -Wl,-rpath,<gmp libdir> is embedded so the build-tree binary and
        # the packaged binary find the conan gmp shared libs at runtime
        # without relying on the device's system libgmp (observed:
        # "Error relocating ./units-filter: __gmpz_* symbol not found"
        # when the loader picked the system stub instead of conan gmp).
        libs = "-lm -lgmpxx -lgmp"
        if libdirs:
            libs = (" ".join("-L%s" % d for d in libdirs) + " "
                    + " ".join("-Wl,-rpath,%s" % d for d in libdirs)
                    + " " + libs)
        self.output.info("CXXFLAGS=%s LIBS=%s" % (cxxflags, libs))

        # NOTE: values contain spaces, so each must be shell-quoted as one
        # make variable assignment. Unquoted `CXXFLAGS=-g -Wall -I...`
        # would make `make` treat `-Wall`, `-I...` as targets and silently
        # drop them (observed: compile line was `clang++ -g -c ...` and
        # gmpxx.h was not found). shlex.quote keeps one assignment.
        self.run(
            "%s -j1 CC=%s CXX=%s RECODE_SUPPORT= CXXFLAGS=%s LIBS=%s" % (
                make, shlex.quote(cc), shlex.quote(cxx),
                shlex.quote(cxxflags), shlex.quote(libs)),
            cwd=src_dir,
            env="conanbuild",
        )
        binary = os.path.join(src_dir, "units-filter")
        if not os.path.isfile(binary):
            raise ConanException("build produced no src/units-filter binary")

        self._run_upstream_tests(src_dir)

    def _neutralize_makefile(self, makefile):
        # Whitespace-tolerant, context-free neutralization of the flex/bison
        # regeneration recipes. The previous conandata patch pinned exact
        # context lines around the rules and failed on-device with
        # "source file is different - b'Makefile'" (fixed hunk vs. real
        # file drift). Editing here avoids conan's patch reader entirely
        # (both its UTF-8 decode and its exact-context match) and tolerates
        # any blank-line/whitespace variation: any TAB-indented recipe line
        # invoking flex/bison becomes a TAB-comment no-op, leaving the
        # targets recipe-less so vendored outputs are never regenerated.
        with open(makefile, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines(True)
        out = []
        neutralized = 0
        for line in lines:
            stripped = line.lstrip(" \t")
            if line.startswith("\t") and (stripped.startswith("flex")
                                           or stripped.startswith("bison")):
                out.append("\t# OHOS vendored: recipe removed\n")
                neutralized += 1
            else:
                out.append(line)
        if neutralized < 2:
            raise ConanException(
                "expected >=2 flex/bison recipes in %s, found %d; "
                "head: %r" % (makefile, neutralized,
                              "".join(lines[:30])[:2000]))
        for line in out:
            s = line.lstrip(" \t")
            if line.startswith("\t") and (s.startswith("flex ")
                                            or s.startswith("flex\t")
                                            or s.startswith("bison ")):
                raise ConanException(
                    "flex/bison recipe remains after neutralization: %r"
                    % line)
        with open(makefile, "w", encoding="utf-8", newline="\n") as f:
            f.writelines(out)
        self.output.info(
            "neutralized %d flex/bison recipes in src/Makefile" % neutralized)

    def _run_upstream_tests(self, src_dir):
        perl = self._conan_perl()
        logfile = os.path.join(self.build_folder, "upstream_tests.log")
        # The upstream harness reads the concatenated fixtures on stdin and
        # prints one "OK ..." line per passing case or a "***ERREUR***"
        # block per failure. The log file is the single deterministic
        # source for the counts below (no stdout scraping, no arithmetic
        # fallbacks).
        # NOTE (2026-10-03 fix): the previous form
        #   self.run("sh -c %s" % cmd, ...)
        # passed the pipeline unquoted, so the outer shell parsed it as
        #   [sh -c cat test.1 ...] | [perl units-test.pl > log]
        # i.e. `sh -c` only received `cat` (rest became $0..$n), plain
        # `cat` then read empty stdin and perl saw empty input -> empty
        # log -> "produced no output" with 0/77 executed. The pipeline
        # must be handed to conan's shell directly (self.run already
        # invokes a shell), with each path quoted as one word, and
        # src_dir prepended to PATH so the harness finds ./units-filter
        # whether it execs a bare or ./-relative name.
        # Runtime libs (stale_runtime_library): the build-tree binary must
        # resolve the conan gmp shared libs, not the device system stub
        # ("Error relocating ./units-filter: __gmpz_* symbol not found",
        # 77/77 failed). rpath above covers the binary itself; the harness
        # spawns it from perl, so also export LD_LIBRARY_PATH for the whole
        # pipeline (a VAR=val prefix would only apply to `cat`, the first
        # stage) and LD_PRELOAD pointing at this build's libgmp/libgmpxx
        # for OHOS loaders that ignore LD_LIBRARY_PATH. Scope is limited
        # to this test command per platform guidance.
        _, run_libdirs = self._gmp_flags()
        ld_path = ":".join(run_libdirs)
        preload_cands = []
        for libdir in run_libdirs:
            for base in ("libgmp.so", "libgmpxx.so"):
                exact = os.path.join(libdir, base)
                if os.path.isfile(exact):
                    preload_cands.append(exact)
                    continue
                for m in sorted(glob.glob(exact + "*")):
                    if os.path.isfile(m):
                        preload_cands.append(m)
                        break
        self.output.info("upstream test runtime: libdirs=%r preload=%r"
                         % (run_libdirs, preload_cands))
        exports = ["export PATH=%s:\"$PATH\"" % shlex.quote(src_dir)]
        if ld_path:
            exports.append("export LD_LIBRARY_PATH=%s:\"$LD_LIBRARY_PATH\""
                           % shlex.quote(ld_path))
        if preload_cands:
            exports.append("export LD_PRELOAD=%s"
                           % shlex.quote(" ".join(preload_cands)))
        cmd = ("%s; PATH=%s:\"$PATH\" cat test.1 test.2 test.3 test.4 | %s units-test.pl > %s 2>&1"
               % ("; ".join(exports), shlex.quote(src_dir),
                  shlex.quote(perl), shlex.quote(logfile)))
        self.run(cmd, cwd=src_dir, env="conanbuild",
                 ignore_errors=True)

        searched = [logfile]
        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("upstream units-test log tail:\n"
                         + "\n".join(out.splitlines()[-15:]))

        passed = sum(1 for line in out.splitlines() if line.startswith("OK"))
        failed = sum(1 for line in out.splitlines()
                     if line.startswith("***ERREUR***"))
        discovered = UPSTREAM_TEST_DISCOVERED
        executed = passed + failed
        skipped = discovered - executed if discovered >= executed else 0
        ok = (failed == 0 and executed == discovered and discovered > 0)

        # Self-check the identities before emitting: passed + failed must
        # equal executed, executed + skipped must not exceed discovered.
        # On violation the marker reports failure with a reason instead of
        # adjusting any number to fit.
        reason = ""
        if passed + failed != executed or executed + skipped > discovered:
            reason = ("count identity violated (passed=%d failed=%d "
                      "executed=%d skipped=%d discovered=%d); log searched: %s"
                      % (passed, failed, executed, skipped, discovered,
                         ", ".join(searched)))
            ok = False
        elif not ok:
            if not os.path.isfile(logfile) or not out.strip():
                reason = ("upstream harness produced no output; searched: %s"
                          % ", ".join(searched))
            else:
                reason = ("upstream harness reports %d/%d failures "
                          "(see upstream_tests.log tail above)" % (failed, executed))

        marker = {
            "status": "passed" if ok else "failed",
            "framework": UPSTREAM_TEST_FRAMEWORK,
            "command": UPSTREAM_TEST_COMMAND,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if reason:
            marker["reason"] = reason
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise ConanException("upstream units-test failed: %s" % (reason or "see log"))

    def package(self):
        copy(self, "units-filter", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        if os.path.isfile(os.path.join(self.source_folder, "units-filter.1")):
            copy(self, "units-filter.1", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "share", "man", "man1"))
        binary = os.path.join(self.package_folder, "bin", "units-filter")
        try:
            os.chmod(binary, 0o755)
        except OSError as exc:
            self.output.warning("chmod on %s failed: %s" % (binary, exc))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
