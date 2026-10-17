#!/usr/bin/env python3
"""Conan recipe — pcg-cpp 0.98.1 (header-only C++11 RNG family, Makefile-driven tests)."""

import json
import os
import shlex
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class PcgCppConan(ConanFile):
    name = "pcg-cpp"
    version = "0.98.1"
    description = (
        "PCG random number generation for C++ — header-only family of "
        "pseudo-random number generators"
    )
    license = "Apache-2.0"
    homepage = "https://www.pcg-random.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _writable_tmpdir(self):
        # HMBS readonly_tmp: /tmp is read-only on the real machine.
        # Reuse the injected TMPDIR/TMP/TEMP when writable, else build tmp.
        for var in ("TMPDIR", "TMP", "TEMP"):
            d = os.environ.get(var)
            if d and os.path.isdir(d):
                try:
                    fd, p = tempfile.mkstemp(dir=d)
                    os.close(fd)
                    os.unlink(p)
                    return d
                except Exception:
                    continue
        d = os.path.join(self.build_folder, "tmp")
        os.makedirs(d, exist_ok=True)
        return d

    def _resolve_cxx(self):
        # Profile tools.build:compiler_executables:cpp may point at
        # /data/service/hnp/bin/clang++ which does not exist on this
        # device (make: No such file or directory, Error 127).
        # Validate the profile path, else fall back to PATH discovery.
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        candidates = []
        profile_cxx = compiler_executables.get("cpp")
        if profile_cxx:
            candidates.append(profile_cxx)
        env_cxx = os.environ.get("CXX")
        if env_cxx:
            candidates.append(env_cxx)
        for name in ("clang++", "c++", "g++"):
            found = shutil.which(name)
            if found and found not in candidates:
                candidates.append(found)
        # Explicit well-known location last (same value profile used).
        if "/data/service/hnp/bin/clang++" not in candidates:
            candidates.append("/data/service/hnp/bin/clang++")
        for cand in candidates:
            if not cand:
                continue
            # Bare names rely on PATH (hmbs prepends toolchain dir).
            if os.path.basename(cand) == cand:
                if shutil.which(cand):
                    return cand
                continue
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        raise RuntimeError(
            "C++ compiler not found (profile cpp=%r, PATH=%r)" % (
                profile_cxx, os.environ.get("PATH", "")))

    def _resolve_make(self):
        for cand in (os.environ.get("HMBS_MAKE"),
                     self.conf.get("user.hmbs:make_path", default=None),
                     shutil.which("make")):
            if cand and (os.path.basename(cand) == cand or
                         (os.path.isfile(cand) and os.access(cand, os.X_OK))):
                if os.path.basename(cand) == cand and not shutil.which(cand):
                    continue
                return cand
        return "make"

    def build(self):
        apply_conandata_patches(self)
        # Upstream test-high/ registers 42 check-* programs (Makefile
        # TARGETS). run-tests.sh executes 41 of them: 40 runs are compared
        # against expected/ golden outputs; check-pcg64_unique runs once
        # with its output discarded (/dev/null); check-pcg32_unique is
        # never invoked by the upstream script. The script itself always
        # exits 0, so pass/fail is judged by re-running the diff here
        # (mechanical exit-code criterion).
        tmpdir = self._writable_tmpdir()
        for k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[k] = tmpdir
        cxx = self._resolve_cxx()
        make_bin = self._resolve_make()
        self.output.info(f"resolved CXX={cxx} MAKE={make_bin} TMPDIR={tmpdir}")
        test_dir = os.path.join(self.source_folder, "test-high")
        make_cmd = (
            f"{shlex.quote(make_bin)} -C {shlex.quote(test_dir)} -j1 "
            f"CXX={shlex.quote(cxx)} "
            f"CPPFLAGS={shlex.quote('-I../include')} "
            f"CXXFLAGS={shlex.quote('-std=c++11 -O1')}"
        )
        self.run(make_cmd)
        self._run_upstream_tests(test_dir)

    def _run_upstream_tests(self, test_dir):
        env = dict(os.environ)
        # Ensure writable TMP for run-tests.sh (readonly /tmp on device).
        tmpdir = env.get("TMPDIR") or env.get("TMP") or env.get("TEMP")
        if tmpdir:
            env["TMPDIR"] = env["TMP"] = env["TEMP"] = tmpdir
        subprocess.run(
            ["sh", "run-tests.sh"],
            cwd=test_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=600,
            check=True,
        )
        # Mechanical verdict: byte-compare every golden output against the
        # actual run in Python. run-tests.sh cannot be trusted by exit code
        # (see comment in build()), and external `diff` is not portable —
        # busybox diff on CI workers rejects `diff -x`.
        # Falsification guard (toybox/GNU pitfall): every compared file must
        # be non-empty, otherwise empty-vs-empty would fake a pass.
        golden_dir = os.path.join(test_dir, "expected")
        actual_dir = os.path.join(test_dir, "actual")
        golden_files = sorted(f for f in os.listdir(golden_dir)
                              if f.endswith(".out"))
        if len(golden_files) != 40:
            raise RuntimeError(
                f"unexpected golden output count: {len(golden_files)} != 40")
        mismatches = []
        for name in golden_files:
            apath = os.path.join(actual_dir, name)
            if not os.path.exists(apath):
                mismatches.append(f"missing actual output: {name}")
                continue
            with open(os.path.join(golden_dir, name), "rb") as gf:
                golden = gf.read()
            with open(apath, "rb") as af:
                actual = af.read()
            if len(golden) == 0 or len(actual) == 0:
                mismatches.append(f"empty output (golden or actual): {name}")
            elif golden != actual:
                mismatches.append(f"content mismatch: {name}")
        out_files = len([f for f in os.listdir(actual_dir)
                         if f.endswith(".out")])
        if mismatches or out_files != len(golden_files):
            detail = "; ".join(mismatches[:5]) or (
                f"actual .out count {out_files} != golden {len(golden_files)}")
            self.output.error(detail)
            raise RuntimeError(
                "upstream test failed: golden mismatch in test-high: "
                + detail)
        # Smoke for the two *_unique programs (no golden outputs upstream).
        # run-tests.sh already runs check-pcg64_unique once with output to
        # /dev/null; check-pcg32_unique is compiled but never invoked by the
        # upstream script, so run it here with the same bare-invocation
        # smoke criterion (exit code 0). Both binaries are self-contained
        # (pcg-test-noadvance harness, no arguments), mirroring the script.
        for prog in ("check-pcg32_unique", "check-pcg64_unique"):
            binpath = os.path.join(test_dir, prog)
            if not os.path.isfile(binpath):
                raise RuntimeError(
                    f"upstream test binary missing after make: {prog}")
            proc = subprocess.run(
                [binpath],
                cwd=test_dir,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                timeout=600,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"upstream smoke test failed: {prog} "
                    f"exited with {proc.returncode}")
        result = {
            "status": "passed",
            "framework": "makefile-programs",
            "command": (
                "make -C test-high -j1 CXX=<profile cpp> "
                "CPPFLAGS=-I../include CXXFLAGS='-std=c++11 -O1'; "
                "sh run-tests.sh; python byte-compare expected/ vs actual/ "
                "(40 golden, non-empty guard); "
                "./check-pcg32_unique + ./check-pcg64_unique smoke (rc==0)"),
            "discovered": 42,
            "executed": 42,
            "passed": 42,
            "failed": 0,
            "skipped": 0,
            "detail": (
                "42 upstream check-* targets compiled and executed: 40 "
                "golden outputs byte-compared (non-empty) + 2 unique "
                "smoke programs with exit-code criterion "
                "(check-pcg64_unique already runs in run-tests.sh; "
                "check-pcg32_unique is compiled but never invoked by the "
                "upstream script, so it is smoke-run here)"),
        }
        marker = ("HMBS_UPSTREAM_TEST_RESULT="
                  + json.dumps(result, ensure_ascii=False))
        self.output.info(marker)
        # Bare print: the hmbs gate scans the raw stdout of the
        # test_package phase; the host build() may additionally be skipped
        # on cache-hit rounds, so test_package re-emits this same marker
        # from the packaged summary (see package() + test_package).
        print(marker, flush=True)
        # Persist for test_package re-emission (cache-hit rounds skip
        # build() entirely, so the marker must be served from the package;
        # proven pattern: python3-cairo res/upstream_test_summary.json).
        try:
            summary_path = os.path.join(
                self.build_folder, "upstream_test_summary.json")
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except OSError as e:
            raise RuntimeError(
                f"failed to write upstream test summary: {e}")

    def package(self):
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # Upstream test evidence for cache-hit rounds (proven pattern:
        # python3-cairo res/upstream_test_summary.json). test_package reads
        # this file and re-emits HMBS_UPSTREAM_TEST_RESULT via bare print,
        # because conan skips build() when the host binary is cached and the
        # hmbs gate only scans the test_package phase stdout.
        summary_src = os.path.join(
            self.build_folder, "upstream_test_summary.json")
        if os.path.isfile(summary_src):
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            copy(self, "upstream_test_summary.json", src=self.build_folder,
                 dst=res_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "pcg-cpp")
        self.cpp_info.set_property("cmake_target_name", "pcg-cpp::pcg-cpp")
