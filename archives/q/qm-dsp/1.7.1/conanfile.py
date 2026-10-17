#!/usr/bin/env python3
"""Conan recipe — qm-dsp 1.7.1 (Makefile static library).

QM-DSP is a C++ library of DSP and Music Informatics functions from the
Centre for Digital Music, Queen Mary University of London. Upstream builds
with plain GNU Makefiles (build/linux/Makefile.linux64) into a static
archive libqm-dsp.a with bundled kissfft/clapack/cblas sources; no
configure, no CMake, no install target.

OHOS adaptations: strip x86-only -msse/-msse2/-mfpmath=sse flags via a
build-time rewrite (_fix_linux_makefile_aarch64), drive CC/CXX/AR/RANLIB from Conan conf (R33), and run
the upstream Boost.Test suite (tests/, 6 binaries, 64 cases) in build()
with valgrind disabled. Evidence is persisted to res/ for test_package
to re-emit as HMBS_UPSTREAM_TEST_RESULT.
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


# Audited count of BOOST_AUTO_TEST_CASE across tests/*.cpp at v1.7.1.
# TestFFT 21 + TestMathUtilities 11 + TestWindow 9 + TestMedianFilter 10
# + TestResampler 11 + TestPhaseVocoder 2 = 64. build() refuses to pass
# if the harness ever reports a different total, so silent skips cannot
# turn into a fake green run.
UPSTREAM_CASE_TOTAL = 64

# Per-binary expectations, used to cross-check the "Running N test cases"
# lines emitted by the Boost.Test framework itself.
UPSTREAM_CASES_PER_BINARY = {
    "test-mathutilities": 11,
    "test-window": 9,
    "test-fft": 21,
    "test-pvoc": 2,
    "test-resampler": 11,
    "test-medianfilter": 10,
}

UPSTREAM_BINARIES = [
    "test-mathutilities",
    "test-window",
    "test-fft",
    "test-pvoc",
    "test-resampler",
    "test-medianfilter",
]


class QmDspConan(ConanFile):
    name = "qm-dsp"
    version = "1.7.1"
    description = "C++ DSP library for Music Informatics (Queen Mary University of London)."
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/c4dm/qm-dsp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("dsp", "audio", "music-information-retrieval", "fft", "chromagram")

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Only needed to compile and run the upstream Boost.Test suite in
        # build(). The library itself bundles kissfft/clapack/cblas and has
        # no other third-party dependency.
        self.requires("boost/1.90.0.4.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Plain Makefile build: no CMake/Meson toolchain file to generate.
        # Compilers are read from conf in build() (R33).
        pass

    def build(self):
        self._fix_linux_makefile_aarch64()
        if not can_run(self):
            self.output.info("cross-building: qm-dsp library built but upstream tests cannot run")
            self._build_library()
            return
        self._build_library()
        result = _run_upstream_tests(self)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        evidence_dir = os.path.join(self.build_folder, "upstream")
        os.makedirs(evidence_dir, exist_ok=True)
        with open(os.path.join(evidence_dir, "upstream_test_result.json"),
                  "w", encoding="utf-8") as f:
            json.dump(result, f)
        if result["status"] != "passed":
            raise ConanException(
                "upstream Boost.Test suite failed: "
                f"{result['passed']}/{result['discovered']} passed"
            )

    def package(self):
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "libqm-dsp.a",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        # Preserve the upstream include layout (dsp/..., base/..., maths/...,
        # hmm/..., thread/..., ext/...) so consumers can keep using
        # #include "dsp/transforms/FFT.h" with -I<package>/include.
        for pattern in ("*.h", "*.hpp"):
            copy(self, pattern,
                 src=self.source_folder,
                 dst=os.path.join(self.package_folder, "include"),
                 keep_path=True)
        copy(self, "upstream_test_result.json",
             src=os.path.join(self.build_folder, "upstream"),
             dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = ["qm-dsp"]
        self.cpp_info.includedirs = ["include"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "qm-dsp")
        self.cpp_info.set_property("cmake_target_name", "qm-dsp::qm-dsp")
        self.cpp_info.set_property("pkg_config_name", "qm-dsp")

    def _fix_linux_makefile_aarch64(self):
        """Strip x86-only SSE flags without a context-sensitive patch.

        The previous patches/0001-*.patch failed in Conan with
        "source file is different - build/linux/Makefile.linux64"
        (hunk context drift / CRLF fragility). Rewriting the single
        CFLAGS line at build time is idempotent and robust: if the
        upstream file no longer contains the x86 flags, it is left
        untouched.
        """
        mk = os.path.join(self.source_folder, "build", "linux",
                          "Makefile.linux64")
        with open(mk, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        fixed = content.replace("-msse2", "").replace("-msse", "")
        fixed = fixed.replace("-mfpmath=sse", "")
        # Collapse any double spaces left by the removals, keep LF.
        while "  " in fixed:
            fixed = fixed.replace("  ", " ")
        if fixed != content:
            with open(mk, "w", encoding="utf-8", newline="\n") as f:
                f.write(fixed)
            self.output.info("patched Makefile.linux64: stripped x86 SSE flags")
        else:
            self.output.info("Makefile.linux64 already aarch64-clean, skip")

    def _compilers(self):
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict) or {}
        cc = self._resolve_tool(
            executables.get("c") or os.environ.get("CC"), "clang")
        cxx = self._resolve_tool(
            executables.get("cpp") or os.environ.get("CXX"), "clang++")
        ar = self._resolve_tool(executables.get("ar"), "llvm-ar")
        ranlib = self._resolve_tool(executables.get("ranlib"), "llvm-ranlib")
        return cc, cxx, ar, ranlib

    def _resolve_tool(self, configured, fallback):
        # Profile configures /data/service/hnp/bin/clang{,++} which is
        # absent on the true device (Error 127). Trust a configured
        # absolute path only when the file exists and is executable;
        # otherwise warn and fall back to PATH (HMBS prepends the real
        # toolchain dirs), keeping the build off the dead absolute path.
        if configured and os.path.isabs(configured):
            if os.path.isfile(configured) and os.access(configured, os.X_OK):
                return configured
            self.output.warning(
                f"compiler path unavailable: {configured}, fallback to PATH")
        elif configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback)
        if found:
            return found
        if configured:
            return configured
        return fallback

    def _build_library(self):
        cc, cxx, ar, ranlib = self._compilers()
        # OHOS-safe flags: upstream Makefile.linux64 hardcodes
        # -msse/-msse2/-mfpmath=sse which clang rejects on aarch64.
        # _fix_linux_makefile_aarch64() removes those; the rest is kept.
        # -stdlib=libc++ matches the OHOS profile (compiler.libcxx=libc++).
        # NOTE: CFLAGS/CXXFLAGS passed on the make command line override the
        # file assignments, so build/general/Makefile.inc's own
        # "CFLAGS := $(CFLAGS) -I. -Iext/kissfft ..." append never applies
        # to command-line values (GNU make command-line precedence). The
        # command line must therefore carry -I. and the kissfft includes plus
        # -Dkiss_fft_scalar=double explicitly, otherwise quoted includes
        # like "maths/MathUtilities.h" fail (base/KaiserWindow.cpp).
        cflags = ("-DNDEBUG -O3 -fPIC -ffast-math -ftree-vectorize -DUSE_PTHREADS"
                  " -I. -Ibuild/linux/amd64 -Iext/kissfft -Iext/kissfft/tools"
                  " -Dkiss_fft_scalar=double")
        cxxflags = cflags + " -stdlib=libc++"
        self.run(
            "make -f build/linux/Makefile.linux64"
            f" CC={cc} CXX={cxx} AR={ar} RANLIB={ranlib}"
            f' CFLAGS="{cflags}" CXXFLAGS="{cxxflags}" -j1',
            cwd=self.source_folder,
        )


def _boost_flags(recipe):
    dep = recipe.dependencies["boost"]

    def _abs(entries):
        out = []
        for entry in entries:
            path = entry if os.path.isabs(entry) else os.path.join(dep.package_folder, entry)
            if os.path.isdir(path):
                out.append(path)
        return out

    includes = _abs(dep.cpp_info.includedirs)
    libdirs = _abs(dep.cpp_info.libdirs)
    return includes, libdirs


def _test_run_env(libdirs):
    # Runtime env: Conan boost dir first (subprocess.run bypasses conanrun).
    env = dict(os.environ)
    prefix = ":".join(p for p in libdirs if p)
    if prefix:
        old = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = prefix + (":" + old if old else "")
    return env


def _run_upstream_tests(recipe):
    """Build the 6 upstream Boost.Test binaries and run them.

    The tests/Makefile 'all' target both builds and runs via valgrind,
    which does not exist on OHOS. Instead the binaries are built by naming
    them explicitly, then each is executed directly (VG="") with the Boost
    framework's own case counting parsed from stdout. A stub binary (wrong
    output, empty output, nonzero exit) fails loudly, and any drift between
    the audited 64 cases and the framework's "Running N test cases" lines
    raises instead of passing silently.
    """
    cc, cxx, ar, ranlib = recipe._compilers()
    includes, libdirs = _boost_flags(recipe)
    inc_flags = " ".join("-I" + p for p in includes)
    lib_flags = " ".join("-L" + p for p in libdirs)
    # RPATH: pin the Conan boost dir so the OHOS loader does not resolve a
    # wrong system copy first (rc=127 Error relocating symbol not found).
    rpath_flags = " ".join("-Wl,-rpath,{}".format(p) for p in libdirs)
    # Compile tests with the same libc++ as the library. -I.. lets the test
    # sources keep using #include "dsp/..." relative to the source root.
    test_cxxflags = (
        "-I.. -Wall -O2 -fPIC -DNDEBUG -std=c++17 -stdlib=libc++ -DBOOST_TEST_DYN_LINK " + inc_flags
    ).strip()
    test_ldflags = (
        f"{lib_flags} {rpath_flags} -lboost_unit_test_framework -lpthread -lm -stdlib=libc++"
    ).strip()
    tests_dir = os.path.join(recipe.source_folder, "tests")
    recipe.run(
        "make {} CXX={} CC={} AR={} RANLIB={} CXXFLAGS=\"{}\" LDFLAGS=\"{}\" VG=\"\" -j1".format(
            " ".join(UPSTREAM_BINARIES), cxx, cc, ar, ranlib, test_cxxflags, test_ldflags
        ),
        cwd=tests_dir,
    )
    discovered = 0
    passed = 0
    failed = 0
    failures = []
    for binary in UPSTREAM_BINARIES:
        exe = os.path.join(tests_dir, binary)
        if not os.path.isfile(exe):
            failed += UPSTREAM_CASES_PER_BINARY[binary]
            failures.append(binary + ":binary-missing")
            recipe.output.error(f"[upstream-test] {binary}: FAIL (binary not built)")
            continue
        proc = subprocess.run(
            [exe, "--log_level=test_suite", "--report_level=detailed"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=tests_dir,
            env=_test_run_env(libdirs),
        )
        try:
            out = proc.stdout.decode("utf-8", errors="replace")
        except Exception:
            out = ""
        # Framework-emitted case count, e.g. "Running 21 test cases...".
        m = re.search(r"Running\s+(\d+)\s+test cases?", out)
        reported = int(m.group(1)) if m else -1
        expected = UPSTREAM_CASES_PER_BINARY[binary]
        ok_exit = proc.returncode == 0
        ok_count = reported == expected
        # --report_level=detailed never prints the short-footer
        # "No errors detected"; its verdict is the per-case
        # "N assertions out of M passed" lines. Require at least one
        # such line (non-empty evidence, anti-stub) and all of them
        # full-pass. Any failure makes Boost print non-full-pass
        # lines and exit nonzero, so this single framework source
        # cannot be fooled by empty output or a stub binary.
        pairs = re.findall(
            r"(\d+)\s+assertions?\s+out of\s+(\d+)\s+passed", out)
        ok_assert = len(pairs) > 0 and all(int(a) == int(b) for a, b in pairs)
        recipe.output.info(f"[upstream-test] {binary}: exit={proc.returncode} reported={reported} expected={expected} full-pass-assert-lines={sum(1 for a, b in pairs if int(a) == int(b))}/{len(pairs)}")
        for line in out.splitlines()[-8:]:
            recipe.output.info(f"[upstream-test] {binary} | {line}")
        if ok_exit and ok_count and ok_assert:
            passed += expected
            discovered += expected
        else:
            discovered += expected
            failed += expected
            reason = []
            if not ok_exit:
                reason.append(f"rc={proc.returncode}")
            if not ok_assert:
                reason.append(f"missing-full-pass-assertions({len(pairs)}-lines)")
            if not ok_count:
                reason.append(f"count-drift-reported={reported}")
            failures.append(f"{binary}:{','.join(reason)}")
            recipe.output.error(f"[upstream-test] {binary}: FAIL ({','.join(reason)})")
    total = discovered
    if total != UPSTREAM_CASE_TOTAL:
        raise ConanException(
            f"upstream harness drift: ran {total} cases, audited {UPSTREAM_CASE_TOTAL}"
        )
    recipe.output.info(f"[upstream-test] {passed}/{total} cases passed; failures={failures}")
    return {
        "status": "passed" if failed == 0 else "failed",
        "framework": "boost-test",
        "command": "make -C tests <6 binaries> VG=\"\" then ./test-* --log_level=test_suite --report_level=detailed",
        "discovered": total,
        "executed": total,
        "passed": passed,
        "failed": failed,
        "skipped": 0,
    }
