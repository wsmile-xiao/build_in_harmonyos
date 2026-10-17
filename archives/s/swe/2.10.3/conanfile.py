#!/usr/bin/env python3
"""Conan recipe for swe 2.10.3 — Swiss Ephemeris (plain Makefile, C99).

Swiss Ephemeris is a high-precision astrology computation library by
Astrodienst (aloistr/swisseph, tag v2.10.3final). Upstream: dual license
AGPL-3.0-or-later / Swiss Ephemeris Professional License.

OHOS adaptation choices:
- Build system: upstream plain Makefile driven via self.run("make ...")
  (same approach as in-tree zlib/1.3.1). No configure step exists.
- R33: compiler taken from Conan conf tools.build:compiler_executables,
  passed as make command-line overrides (CC=... CFLAGS=...), never from
  bare shell environment variables.
- Only the portable targets are built: libswe.a, libswe.so, swetest,
  swemini. The fully-static swetests target (-Wl,-Bstatic) is skipped:
  static-link groups are not portable to the OHOS loader.
- Upstream test: the setest C harness (setest/, 10 suite_*.c suites) needs
  libcrypto + m4 + perl plus JPL-scale ephemeris data at build time, so the
  build sandbox instead runs upstream's own swetest binary (the same program
  Debian ships as the "swetest" test application) in Moshier mode
  (-emos, no ephemeris files needed) with 3 deterministic invocations whose
  numeric output is verified non-empty. See notes.md for the audit.
"""
import glob
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.layout import basic_layout


class SweConan(ConanFile):
    name = "swe"
    version = "2.10.3"
    description = "High precision Swiss Ephemeris library for astrological computation"
    license = "AGPL-3.0-or-later"
    homepage = "https://www.astro.com/swisseph/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # Upstream setest suites (suite_01 .. suite_10), the official test units.
    _UPSTREAM_SUITES = 10
    # swetest smoke invocations executed in build() (Moshier mode, offline).
    _SMOKE_CASES = [
        "./swetest -b1.1.2000 -p0 -emos -head",
        "./swetest -b1.1.2000 -p1 -emos -head",
        "./swetest -b15.6.1990 -p3 -emos -head",
    ]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # libswe itself only needs libm/libdl from the system: no Conan deps.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_cc(self):
        try:
            conf_cc = self.conf.get("tools.build:compiler_executables:c", check_type=str)
        except Exception:
            conf_cc = None
        if conf_cc and os.path.isfile(conf_cc):
            return conf_cc
        return conf_cc or "clang"

    def _resolve_make(self):
        make_env = os.environ.get("HMBS_MAKE", "")
        if make_env and os.path.isfile(make_env):
            return make_env
        return "make"

    def _fix_swetest_spmoon(self):
        # v2.10.3final swetest.c uses `spmoon` at the -xv handler (~1139)
        # and the 'v' dispatch (~1621) without any declaration (only
        # star/sastno/shyp are declared) -> clang hard error. Later
        # upstream (c353e6f) reuses `sastno` for this path, so backport
        # that exact semantic via in-recipe replacement (avoids unified
        # diff hunk bookkeeping). v2.10.3final has exactly 3 `spmoon`
        # occurrences, all in swetest.c, so a scoped rename is safe.
        swetest = os.path.join(self.source_folder, "swetest.c")
        replace_in_file(self, swetest, "spmoon", "sastno")
        self.output.info("swe build: backported upstream spmoon->sastno fix in swetest.c")

    def build(self):
        apply_conandata_patches(self)
        self._fix_swetest_spmoon()
        cc = self._resolve_cc()
        make = self._resolve_make()
        self.output.info("swe build: CC={} MAKE={}".format(cc, make))
        # R33: CC/CFLAGS as make command-line overrides (override the
        # Makefile's hardcoded CC=cc). -j1: HMDFS jobserver constraint.
        # Clean first: conan build folders may be reused across preflight
        # rounds; stale/corrupt .o or a stale libswe.so would otherwise be
        # treated as up-to-date by make and produce a shared lib with
        # missing symbols (observed: "Error relocating ./swetest" for
        # swecl/swehel/swephlib symbols). Ignore clean errors (fresh tree).
        try:
            self.run('{make} clean'.format(make=make), cwd=self.source_folder)
        except ConanException as exc:
            self.output.warning("swe build: make clean failed (ignored): {!r}".format(exc))
        # Build objects + libs via upstream Makefile first.
        self.run(
            '{make} -j1 CC="{cc}" CFLAGS="-O2 -fPIC -Wall" '
            "libswe.a libswe.so swetest.o swemini.o".format(make=make, cc=cc),
            cwd=self.source_folder,
        )
        self._verify_lib_symbols()
        # Link verification binaries statically against ./libswe.a
        # (explicit path, not -L. -lswe): upstream `swetest` rule prefers
        # libswe.so when both .a/.so exist, which makes smoke tests depend
        # on the loader path and on every symbol being exported from .so.
        # Static linking tests the same objects packaged by default
        # (shared=False) and removes the "Error relocating" failure mode.
        self.run(
            '"{cc}" -O2 -fPIC -Wall -o swetest swetest.o ./libswe.a -lm -ldl'.format(cc=cc),
            cwd=self.source_folder,
        )
        self.run(
            '"{cc}" -O2 -fPIC -Wall -o swemini swemini.o ./libswe.a -lm -ldl'.format(cc=cc),
            cwd=self.source_folder,
        )
        self._run_upstream_tests()

    def _verify_lib_symbols(self):
        """Fail fast if the just-built libs lack smoke-test symbols.
        Single deterministic source: `nm -g` over built archives."""
        import shutil
        import subprocess
        required = [
            "swe_calc_ut",
            "swe_sol_eclipse_when_loc",
            "swe_lun_occult_where",
            "swe_heliacal_ut",
            "swe_nod_aps",
            "swe_d2l",
            "swe_orbit_max_min_true_distance",
        ]
        nm = shutil.which("nm") or shutil.which("llvm-nm")
        for fname in ("libswe.a", "libswe.so"):
            path = os.path.join(self.source_folder, fname)
            try:
                size = os.path.getsize(path)
            except OSError:
                raise ConanException("swe build: expected artifact missing: {}".format(path))
            self.output.info("swe build: artifact {} size={}".format(fname, size))
            if size == 0:
                raise ConanException("swe build: artifact empty: {}".format(path))
            if not nm:
                self.output.warning("swe build: nm not found, skipping symbol check")
                continue
            try:
                proc = subprocess.run(
                    [nm, "-g", path],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    cwd=self.source_folder, timeout=120,
                )
                out = proc.stdout.decode("utf-8", errors="replace")
            except Exception as exc:
                self.output.warning("swe build: nm failed on {} ({!r})".format(fname, exc))
                continue
            missing = [s for s in required if s not in out]
            self.output.info("swe build: nm -g {} -> {} bytes, missing={}".format(fname, len(out), missing))
            if missing:
                raise ConanException("swe build: {} missing symbols {}".format(fname, missing))

    def _run_upstream_tests(self):
        """Run upstream swetest smoke cases, verify numeric output, emit the
        HMBS_UPSTREAM_TEST_RESULT evidence marker (dual channel) and persist
        the summary so test_package can re-emit it on cache hits."""
        logs = []
        passed = 0
        failed = 0
        for idx, cmd in enumerate(self._SMOKE_CASES):
            log_path = os.path.join(self.build_folder, "swe-smoke-{}.log".format(idx))
            try:
                self.run('{} > "{}" 2>&1'.format(cmd, log_path), cwd=self.source_folder)
                rc = 0
            except ConanException:
                rc = 1
            output = ""
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                    output = handle.read()
            except OSError:
                output = ""
            logs.append(output)
            # Deterministic single source: the case passes only when the
            # process exits 0 AND stdout holds a floating point ephemeris
            # value (guards against empty-output false passes). No stdout
            # word counting, no guessing fixups.
            if rc == 0 and output.strip() and re.search(r"\d+\.\d+", output):
                passed += 1
                self.output.info("swe smoke case {} passed: {}".format(idx, cmd))
            else:
                failed += 1
                self.output.error(
                    "swe smoke case {} failed (rc={}): {} output tail: {}".format(
                        idx, rc, cmd, output.strip()[-500:]
                    )
                )
        discovered = self._count_upstream_suites()
        executed = len(self._SMOKE_CASES)
        # Self-check identities: any violation means a parse bug -> fail closed.
        if passed + failed != executed:
            raise ConanException(
                "swe upstream parse bug: passed({}) + failed({}) != executed({})".format(
                    passed, failed, executed
                )
            )
        # Dual verdict: core self-consistency vs full official coverage.
        # passed only when executed == official total (discovered). Core
        # green but partial (3 smoke of 10 suites) emits failed + gaps +
        # reason and lets the build succeed; only true core failure or a
        # parse violation raises.
        core_ok = (failed == 0 and passed == executed and passed > 0)
        full = (core_ok and executed == discovered)
        status = "passed" if full else "failed"
        summary = {
            "status": status,
            "framework": "swetest",
            "command": " ; ".join(self._SMOKE_CASES),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        if passed < discovered:
            summary["gaps"] = [
                {
                    "count": discovered - passed,
                    "category": "environment",
                    "detail": "setest C harness suites not executed in the build "
                              "sandbox (needs libcrypto + m4 + perl build tools "
                              "and JPL-scale ephemeris data at build time); "
                              "swetest Moshier-mode smoke covers core swe_calc "
                              "paths instead",
                    "evidence": "setest/Makefile LIBS=-lcrypto; top Makefile "
                                "'test: cd setest && make && ./setest t'; "
                                "readme.md ephemeris download section",
                }
            ]
            if core_ok:
                summary["reason"] = (
                    "core smoke {}/{} passed; {} of {} official setest suites "
                    "not run in build sandbox (see gaps)".format(
                        passed, executed, discovered - passed, discovered
                    )
                )
        summary_path = os.path.join(self.build_folder, "upstream_test_summary.json")
        with open(summary_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(summary, ensure_ascii=False))
        self.output.info("swe upstream test summary written: {}".format(summary_path))
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(summary, ensure_ascii=False)
        self.output.info(line)
        print(line, flush=True)
        if not core_ok:
            raise ConanException(
                "swe upstream smoke tests failed: " + json.dumps(summary, ensure_ascii=False)
            )

    def _count_upstream_suites(self):
        """Count the official setest suites (setest/suite_*.c) in the source
        tree. Single deterministic file source, falls back honestly."""
        pattern = os.path.join(self.source_folder, "setest", "suite_*.c")
        found = sorted(glob.glob(pattern))
        if len(found) == self._UPSTREAM_SUITES:
            return self._UPSTREAM_SUITES
        raise ConanException(
            "swe upstream audit: expected {} setest suites, found {} at {}".format(
                self._UPSTREAM_SUITES, len(found), pattern
            )
        )

    def package(self):
        src = self.source_folder
        copy(self, "libswe.a", src=src, dst=os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            copy(self, "libswe.so", src=src, dst=os.path.join(self.package_folder, "lib"))
        else:
            # Static-first on OHOS (avoids .so code-signing); shared build
            # still available via -o swe/*:shared=True.
            for stale in glob.glob(os.path.join(self.package_folder, "lib", "libswe.so*")):
                try:
                    os.remove(stale)
                except OSError:
                    pass
        copy(self, "*.h", src=src, dst=os.path.join(self.package_folder, "include"))
        # Persist the measured upstream result for per-round re-emit.
        summary_src = os.path.join(self.build_folder, "upstream_test_summary.json")
        if os.path.isfile(summary_src):
            copy(
                self,
                "upstream_test_summary.json",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "res"),
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.libs = ["swe"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("m")
