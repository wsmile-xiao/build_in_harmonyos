#!/usr/bin/env python3
"""Conan recipe — libcorrect 0.0-git20260204 (CMake, C99).

libcorrect is a BSD-licensed C library implementing forward error
correction: Reed-Solomon block codes (encode/decode, with erasures) and
convolutional codes with a soft-decision Viterbi decoder — a drop-in
BSD-licensed substitute for libfec (it even ships an optional libfec API
compatibility shim). Upstream: quiet/libcorrect, master line (the project
has never cut a tagged release). This recipe pins the GitHub codeload
snapshot of refs/heads/master by sha256; the tarball's pax global header
records commit ee82e6673a806dfdf0a969b975ab36596ecc5401.

OHOS adaptation notes (verified natively on an OHOS aarch64 worker,
2026-10-02):
- W0 dependency audit: the library needs nothing beyond libc
  (nm -D on the built .so shows only calloc/free/malloc/memcpy/memset/
  printf/putchar/puts; the tests additionally link m). Upstream tests
  do NOT use the check framework — they are hand-rolled C mains
  registered via CTest — so no test-framework conan node is required
  and no upstream test had to be trimmed: all 4 unconditionally
  registered ctest entries run natively inside build().
- Zero patches. Upstream CMake configures and builds unchanged under
  CMAKE_SYSTEM_NAME=OHOS: the SSE4.1 probe (x86intrin.h) and the system
  libfec probe (find_library(FEC fec)) both fail on aarch64/OHOS, which
  is upstream's own platform gating doing its job (the SSE- and
  libfec-conditional tests are not registered — the same happens on
  upstream's own GitHub CI runners, which also lack libfec).
- Test integration: enable_testing() lives in tests/CMakeLists.txt
  (not at top level), so a root-level `ctest` reports
  "No tests were found". build() therefore builds the
  EXCLUDE_FROM_ALL "test_runners" aggregate target explicitly and runs
  ctest from build/tests/. Counts come solely from
  Testing/Temporary/LastTest.log via a fail-closed parser (libbgcode
  precedent): discovered is the M denominator of the per-test
  `N/M Testing:` headers, passed/failed/skipped come from the
  `Test Passed.` / `***Test Failed.` verdict footers. A missing or
  malformed log, or any non-passed entry, fails the build instead of
  faking green.
- Packaging: upstream unconditionally builds BOTH libcorrect.so and
  libcorrect.a (explicit add_library SHARED/STATIC keywords override
  BUILD_SHARED_LIBS), and the two "shim" tests additionally build a
  libfec API-compat shim that upstream's install(... OPTIONAL) then
  ships as libfec.a once it exists. package() keeps only the selected
  variant and prunes the fec shim (and its fec.h header) so this
  package can never shadow the real libfec package.
- Known limitation (documented; default unaffected): the upstream
  shared object carries no SONAME, so shared=True consumers get the
  package path baked into DT_NEEDED (libaec/E077 family caveat). The
  default is static, which avoids this entirely.
"""

import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, rm

required_conan_version = ">=2.0"


class LibcorrectConan(ConanFile):
    name = "libcorrect"
    version = "0.0-git20260204"
    description = (
        "libcorrect — C library for forward error correction: "
        "Reed-Solomon codes and convolutional codes with soft-decision "
        "Viterbi decoding (BSD-licensed libfec substitute)"
    )
    license = "BSD-3-Clause"
    homepage = "https://github.com/quiet/libcorrect"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("fec", "error-correction", "reed-solomon", "convolutional", "viterbi")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass  # no third-party dependencies (pure C, libc only)

    def validate(self):
        # R32: only the OHOS/Linux family is validated.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libcorrect %s supports Linux and OHOS, got os=%s"
                % (self.version, self.settings.os)
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # upstream installs into lib/ (never lib64)
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        if self.settings.os == "OHOS":
            # E092 / libaec / leptonica / libbgcode precedent: the
            # OHOS-adapted conan maps os=OHOS to
            # CMAKE_SYSTEM_NAME=HarmonyOS, but the OHOS SDK platform
            # module on the workers is Platform/OHOS — pin it
            # explicitly (guarded by os so other profiles are untouched).
            # A side effect (a welcome one): explicitly setting the
            # system name marks the configure as cross, which skips
            # upstream's -march=native SSE4.1 probe — on aarch64 that
            # probe cannot compile anyway.
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # All upstream test executables are EXCLUDE_FROM_ALL; the
        # aggregate "test_runners" target is the upstream-documented way
        # to build them (upstream's own `make check` depends on it).
        cmake.build(target="test_runners")
        self._run_upstream_tests()

    # ── upstream test execution ────────────────────────────────────

    def _run_upstream_tests(self):
        """Run the upstream ctest suite; counts come only from LastTest.log.

        Single deterministic source: <build>/tests/Testing/Temporary/
        LastTest.log written by ctest. discovered = suite size
        denominator, executed / passed / failed / skipped from the
        per-test status words. Any other outcome (missing log,
        unparsable line, counts violating the identities) fails the
        build with a reason instead of guessing.
        """
        if not can_run(self):
            raise ConanException(
                "libcorrect upstream tests must run natively; "
                "cross-building without a runnable target is not supported"
            )
        # enable_testing() is in tests/CMakeLists.txt, so the ctest
        # entries live in the tests subdirectory: run ctest there first
        # (root-level ctest would report "No tests were found").
        dirs = []
        for cand in (
            os.path.join(self.build_folder, "tests"),
            self.build_folder,
        ):
            if cand not in dirs and os.path.isfile(
                os.path.join(cand, "CTestTestfile.cmake")
            ):
                dirs.append(cand)
        if not dirs:
            raise ConanException(
                "libcorrect: no CTestTestfile.cmake under %s" % self.build_folder
            )
        command = "ctest --output-on-failure"
        last = None
        for ctest_dir in dirs:
            self.run(command, cwd=ctest_dir, env="conanrun", ignore_errors=True)
            marker = self._parse_ctest_log(self.build_folder, command)
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
            )
            if marker["status"] == "passed":
                return
            last = marker
        raise ConanException(
            "libcorrect upstream ctest failed: "
            "discovered=%(discovered)d executed=%(executed)d "
            "passed=%(passed)d failed=%(failed)d skipped=%(skipped)d "
            "reason=%(reason)s" % last
        )

    @staticmethod
    def _find_last_test_logs(build_folder):
        """Candidate LastTest.log paths, primary first then recursive walk.

        cmake_layout may place the real CTest tree one level below
        self.build_folder (build/Release), and this recipe's tests live
        another level down (build/tests), so a single fixed path is
        fail-open by construction: walk capped at depth 6 instead.
        """
        candidates = [
            os.path.join(build_folder, "Testing", "Temporary", "LastTest.log")
        ]
        try:
            if os.path.isdir(build_folder):
                base_depth = build_folder.count(os.sep)
                for cur, _dirs, files in os.walk(build_folder):
                    if "LastTest.log" in files:
                        full = os.path.join(cur, "LastTest.log")
                        if full not in candidates:
                            candidates.append(full)
                    if cur.count(os.sep) - base_depth > 6:
                        try:
                            _dirs[:] = []
                        except Exception:
                            pass
        except Exception:
            pass
        return candidates

    @staticmethod
    def _parse_ctest_log(build_folder, command):
        """Parse Testing/Temporary/LastTest.log into an HMBS marker dict.

        Single deterministic source: the LastTest.log file written by
        ctest. discovered: the M denominator of the per-test
        `N/M Testing:` / `N/M Test:` headers (every entry must agree,
        else fail closed). passed/failed/skipped: the per-test verdict
        phrases `Test Passed.` / `***Test Failed.` / `Test Timeout` /
        `Test Skipped` (libwmime precedent for the real LastTest.log
        format). NOTE: ctest prints `N/M Test #K:` lines only on
        stdout; LastTest.log carries the verdict on its own footer
        lines, so a stdout-style pattern never matches here. No stdout
        counting and no arithmetic patching: numbers have one source,
        identities are checked, every failure carries a reason.
        """
        candidates = LibcorrectConan._find_last_test_logs(build_folder)
        existing = [p for p in candidates if os.path.isfile(p)]
        non_empty = []
        for path in existing:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
            except OSError:
                continue
            if content.strip():
                non_empty.append((path, content))
        if not non_empty:
            detail = "searched %s" % ", ".join(candidates)
            if existing:
                detail += " (all %d existing file(s) empty)" % len(existing)
            return {
                "status": "failed",
                "framework": "ctest",
                "command": command,
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "LastTest.log holds no test entries; %s" % detail,
            }

        def _entry_count(item):
            _path, _content = item
            return len(re.findall(r"(?m)^\s*\d+/\d+\s+Test(?:ing)?:", _content))

        non_empty.sort(key=_entry_count)
        log_path, content = non_empty[-1]
        try:
            content = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", content)
        except Exception:
            pass
        sizes = set(
            int(match.group(1))
            for match in re.finditer(
                r"(?m)^\s*\d+/(\d+)\s+Test(?:ing)?:", content)
        )
        if len(sizes) != 1:
            return {
                "status": "failed",
                "framework": "ctest",
                "command": command,
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "LastTest.log suite denominators disagree %s in %s"
                % (sorted(sizes), log_path),
            }
        discovered = sizes.pop()
        # Four disjoint verdict phrases, counted once each in a single
        # pass: "***Test Failed." contains "Test Failed" but never
        # "***Failed", so plain addition cannot double-count.
        passed = len(re.findall(r"Test Passed", content))
        failed = len(re.findall(r"Test Failed", content))
        failed += len(re.findall(r"Test Timeout", content))
        failed += len(re.findall(r"\*\*\*Failed", content))
        failed += len(re.findall(r"\*\*\*Timeout", content))
        skipped = len(re.findall(r"Test Skipped", content))
        skipped += len(re.findall(r"\*\*\*Skipped", content))
        executed = passed + failed
        if discovered == 0 or passed + failed + skipped == 0:
            return {
                "status": "failed",
                "framework": "ctest",
                "command": command,
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "LastTest.log holds no test entries; read %s"
                % log_path,
            }
        # Self-check identities; never patch numbers to fit.
        if not (passed + failed == executed
                and executed + skipped <= discovered
                and executed <= discovered):
            return {
                "status": "failed",
                "framework": "ctest",
                "command": command,
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "count identities violated "
                "(discovered=%d executed=%d passed=%d failed=%d skipped=%d) "
                "in %s" % (discovered, executed, passed, failed,
                            skipped, log_path),
            }
        if failed == 0 and skipped == 0 and executed == discovered:
            return {
                "status": "passed",
                "framework": "ctest",
                "command": command,
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "reason": "all %d tests passed (%s)"
                % (passed, log_path),
            }
        return {
            "status": "failed",
            "framework": "ctest",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "reason": "%d/%d passed, %d failed, %d skipped (%s)"
            % (passed, discovered, failed, skipped, log_path),
        }

    # ── packaging ──────────────────────────────────────────────────

    def package(self):
        cmake = CMake(self)
        cmake.install()
        lib_dir = os.path.join(self.package_folder, "lib")
        # The libfec API-compat shim (src/fec_shim.c) exists only as a
        # build-time dependency of the two "shim" tests; upstream's
        # install(TARGETS ... OPTIONAL) ships it as libfec.a once the
        # tests built it. Never package it (or its fec.h): this package
        # must not shadow the real libfec package.
        rm(self, "libfec.*", lib_dir)
        rm(self, "fec.h", os.path.join(self.package_folder, "include"))
        # Upstream always builds both variants (explicit SHARED/STATIC
        # keywords in add_library override BUILD_SHARED_LIBS): keep
        # only the selected one.
        if self.options.shared:
            rm(self, "libcorrect.a", lib_dir)
            keep = "libcorrect.so"
        else:
            rm(self, "libcorrect.so*", lib_dir)
            keep = "libcorrect.a"
        # Fail closed on the expected artifacts.
        for path in (
            os.path.join(lib_dir, keep),
            os.path.join(self.package_folder, "include", "correct.h"),
        ):
            if not os.path.isfile(path):
                raise ConanException(
                    "libcorrect package missing %s (lib dir: %s)"
                    % (path, os.listdir(lib_dir) if os.path.isdir(lib_dir) else "?")
                )

    def package_info(self):
        # Upstream installs no CMake config files of its own; expose the
        # canonical name so consumers can find_package(correct) and link
        # correct::correct (lcrq precedent for config-less C libraries).
        self.cpp_info.set_property("cmake_file_name", "correct")
        self.cpp_info.set_property("cmake_target_name", "correct::correct")
        self.cpp_info.set_property("pkg_config_name", "correct")
        self.cpp_info.libs = ["correct"]
        # Public header layout is flat: #include <correct.h>
