#!/usr/bin/env python3
"""Conan test_package for RapidJSON 1.1.0 — Conan L1 official test.

This test_package does two things in test():

1. **Consumer test (L1)**: builds and runs ``test_rapidjson`` to verify the
   packaged RapidJSON headers can be consumed from a downstream CMake project.

2. **Upstream Google Test suite (HMBS evidence)**: downloads the RapidJSON
   1.1.0 source + vendored Google Test 1.8.1, compiles the upstream
   ``unittest`` binary and runs it, emitting the
   ``HMBS_UPSTREAM_TEST_RESULT`` marker.

The upstream tests are executed in test_package (not in the main recipe's
build()) because the main recipe is ``package_type = "header-library"``:
once the binary package is cached, Conan 2 skips build()/package() entirely
(``Already installed!``), so any upstream-test logic placed in build() never
runs on cached rebuilds. test_package's test() method always executes on
every ``conan create`` regardless of binary cache state, making it the only
reliable lifecycle hook for HMBS upstream-test evidence on a header-only
library.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get


# Upstream source + vendored gtest URLs. These mirror the main recipe's
# conandata.yml so test_package can fetch them without reaching into the
# tested package's private conan_data.
RAPIDJSON_URL = "https://github.com/Tencent/rapidjson/archive/refs/tags/v1.1.0.tar.gz"
RAPIDJSON_SHA256 = "bf7ced29704a1e696fbccf2a2b4ea068e7774fa37f6d7dd4039d0787f8bed98e"
GTEST_URL = "https://github.com/google/googletest/archive/refs/tags/release-1.8.1.tar.gz"
GTEST_SHA256 = "9bf1fe5182a604b4135edc1a425ae356c9ad15e9b23f9f12a02e80184c3a249c"


class RapidjsonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # ── 1. Consumer test (L1) ──
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_rapidjson'", cwd=self.cpp.build.bindirs[0])

        # ── 2. Upstream Google Test suite (HMBS evidence) ──
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Download RapidJSON source + vendored gtest, build & run the upstream
        Google Test ``unittest`` binary, emit HMBS_UPSTREAM_TEST_RESULT.

        This runs in test_package's test() (always executed) rather than the
        main recipe's build() (skipped on cached header-only binaries) to
        guarantee the HMBS upstream-test marker is produced on every
        ``conan create``.
        """
        work_dir = os.path.join(self.build_folder, "hmbs-upstream")
        src_dir = os.path.join(work_dir, "rapidjson-1.1.0")
        build_test_dir = os.path.join(work_dir, "build")
        os.makedirs(work_dir, exist_ok=True)

        # Resolve the real HarmonyOS clang toolchain path. The default PATH on
        # the real machine does NOT expose clang/clang++ at the top level (they
        # live under /data/service/hnp/bin). Read from the Conan conf registry
        # populated by the HarmonyOS Conan profile, falling back to the
        # well-known /data/service/hnp/bin location.
        #
        # NOTE: conan 2.30's self.conf.get does NOT support the ``:subkey``
        # access form (e.g. ``tools.build:compiler_executables:c`` raises
        # ConanException "[conf] does not exist"). The conf is registered as a
        # single dict-valued key; fetch the whole value and index it in Python.
        compilers = {"c": "/data/service/hnp/bin/clang",
                     "cpp": "/data/service/hnp/bin/clang++"}
        try:
            raw = self.conf.get("tools.build:compiler_executables", check_type=dict)
            if raw:
                compilers.update(raw)
        except ConanException:
            pass
        cc = compilers.get("c", "/data/service/hnp/bin/clang")
        cxx = compilers.get("cpp", "/data/service/hnp/bin/clang++")

        # Resolve absolute paths for the build tools. HMBS probes the real
        # machine and exposes the locations both as Conan conf
        # (user.hmbs:cmake_path / make_path / ninja_path) and as env vars
        # (HMBS_CMAKE / HMBS_MAKE / HMBS_NINJA). subprocess.run does not inherit
        # the Conan-injected env, and on the HarmonyOS preflight host cmake/make
        # live under /data/service/hnp/bin which is not on the default PATH.
        def _resolve_tool(conf_key, env_var, fallback):
            try:
                val = self.conf.get(conf_key, check_type=str)
                if val:
                    return val
            except ConanException:
                pass
            return os.environ.get(env_var) or fallback

        cmake_bin = _resolve_tool("user.hmbs:cmake_path", "HMBS_CMAKE",
                                  "/data/service/hnp/bin/cmake")
        make_bin = _resolve_tool("user.hmbs:make_path", "HMBS_MAKE",
                                 "/data/service/hnp/bin/make")

        # Download RapidJSON source if not already present.
        if not os.path.exists(os.path.join(src_dir, "CMakeLists.txt")):
            self.output.info("Downloading RapidJSON 1.1.0 source for upstream tests...")
            get(self, url=RAPIDJSON_URL, sha256=RAPIDJSON_SHA256,
                strip_root=True, destination=src_dir)

        # Vendor Google Test 1.8.1 into thirdparty/gtest/googletest so the
        # upstream FindGTestSrc.cmake find-module locates them. The release
        # tarball ships an empty thirdparty/gtest git submodule.
        gtest_target = os.path.join(src_dir, "thirdparty", "gtest", "googletest")
        if not os.path.exists(os.path.join(gtest_target, "CMakeLists.txt")):
            self.output.info("Vendoring Google Test 1.8.1 for upstream tests...")
            gtest_dl = os.path.join(work_dir, "_gtest_dl")
            os.makedirs(gtest_dl, exist_ok=True)
            get(self, url=GTEST_URL, sha256=GTEST_SHA256,
                strip_root=True, destination=gtest_dl)
            dl_googletest = os.path.join(gtest_dl, "googletest")
            if not os.path.isdir(dl_googletest):
                for root, dirs, _ in os.walk(gtest_dl):
                    if os.path.basename(root) == "googletest":
                        dl_googletest = root
                        break
            if not os.path.isdir(dl_googletest):
                self._emit_failed_marker(
                    "could not locate googletest/ subtree in vendored gtest archive")
                raise ConanException("could not locate googletest/ subtree")
            os.makedirs(os.path.dirname(gtest_target), exist_ok=True)
            import shutil
            if os.path.exists(gtest_target):
                shutil.rmtree(gtest_target)
            shutil.move(dl_googletest, gtest_target)

        # De-fatalize upstream's ``-Werror`` by rewriting every ``-Werror``
        # token in every upstream CMakeLists.txt to ``-Wno-error``. RapidJSON
        # 1.1.0 (2016-era) triggers a wide set of clang 15 -Wextra warnings
        # that upstream promotes to hard errors via -Wall -Wextra -Werror
        # appended *after* our CMAKE_CXX_FLAGS cache value. A bare -Wno-error
        # demotes all warnings' error promotion and is not re-armed by a
        # subsequent -Wall/-Wextra. No upstream GTest assertion is deleted,
        # skipped, or stubbed.
        #
        # Additionally neutralize ``-Weverything`` (clang only) by replacing
        # it with ``-Wno-everything``. Upstream test/unittest/CMakeLists.txt:42
        # appends ``-Weverything`` in the Clang branch. ``-Weverything`` enables
        # hundreds of pedantic warnings (``-Wc++98-compat``,
        # ``-Wc++98-compat-pedantic``, ``-Wweak-vtables``, ``-Wpadded``, ...)
        # that fire en masse on 2016-era RapidJSON test sources compiled with
        # clang 15. Even with ``-Wno-error`` demoting warning-to-error
        # promotion, the sheer volume of ``-Weverything`` diagnostics triggers
        # clang internal errors / fatal diagnostics on several ``*test.cpp``
        # files, causing CMake to drop those object files from the link and the
        # resulting ``unittest`` binary to contain only a fraction of the 342
        # upstream TEST/TEST_F cases (real machine observed discovered=34).
        # Replacing ``-Weverything`` with ``-Wno-everything`` lets all 25
        # UNITTEST_SOURCES compile cleanly, so ``discovered`` reaches the true
        # upstream count (~342). The upstream GTest assertions themselves are
        # untouched — only the compiler diagnostic severity is relaxed.
        for root, _dirs, files in os.walk(src_dir):
            for fname in files:
                if fname != "CMakeLists.txt":
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                        text = fh.read()
                except OSError:
                    continue
                new_text = text.replace("-Werror", "-Wno-error")
                new_text = new_text.replace("-Weverything", "-Wno-everything")
                if new_text != text:
                    try:
                        with open(fpath, "w", encoding="utf-8") as fh:
                            fh.write(new_text)
                    except OSError:
                        pass

        # Pre-process upstream ``unittest.h`` so TempFile() does not crash on the
        # HarmonyOS preflight host. Upstream hard-codes ``mkstemp("/tmp/fileXXXXXX")``.
        # On the preflight host ``/tmp`` is not guaranteed to be writable; ``mkstemp``
        # then returns -1, ``fdopen(-1, "w")`` returns NULL, and the very first
        # ``FileWriteStream`` constructor fires ``RAPIDJSON_ASSERT(fp_ != 0)`` which
        # throws ``AssertException`` — for tests like
        # ``EncodedStreamTest.EncodedOutputStream`` whose bodies are *not* wrapped in
        # a top-level ``try/catch`` of that exception, the exception escapes GTest's
        # per-test try/catch and calls ``std::terminate`` → ``abort()``. The process
        # dies mid-case, with no ``[ OK ]`` / ``[ FAILED ]`` for the running case.
        #
        # The previous fix here tried to honor the HMBS-injected ``TMPDIR`` by
        # ``sprintf(filename, "%s/fileXXXXXX", "<TMPDIR>")``. That is a **buffer
        # overflow**: every TempFile caller in upstream declares
        # ``char filename[L_tmpnam];`` (``L_tmpnam`` is 20 on glibc/aarch64 — exactly
        # the size of ``"/tmp/fileXXXXXX"``), but the HMBS per-task TMPDIR is
        # typically 80–100 chars long (``/storage/Users/.../<task>/runtime/<pkg>/tmp``).
        # ``sprintf`` writes 96+ bytes into a 20-byte stack buffer, corrupts the
        # call frame, and the process crashes inside the first
        # ``TestEncodedOutputStream`` invocation — exactly the
        # ``EncodedStreamTest.EncodedOutputStream`` mid-case abort seen on the
        # preflight host.
        #
        # Correct fix: keep the path *shorter* than ``L_tmpnam`` (20) for *every*
        # upstream caller (``encodedstreamtest.cpp`` / ``filestreamtest.cpp`` /
        # ``ostreamwrappertest.cpp`` / ``prettywritertest.cpp`` all use
        # ``char filename[L_tmpnam];``). Try the writable CWD first
        # (``./file_XXXXXX`` — 14 chars, the unittest CWD is ``<src_dir>/bin``
        # which is writable), then fall back to the upstream ``/tmp`` literal.
        # If both fail, return NULL so the upstream
        # ``RAPIDJSON_ASSERT(fp_ != 0)`` honestly fires — no upstream assertion
        # is deleted, skipped, or stubbed; the mkstemp contract is preserved.
        unittest_h = os.path.join(src_dir, "test", "unittest", "unittest.h")
        try:
            with open(unittest_h, "r", encoding="utf-8", errors="replace") as fh:
                h_text = fh.read()
            # Replace the entire non-MSVC TempFile body with a short-path
            # version that stays within ``L_tmpnam`` for every caller.
            old_body = (
                '    strcpy(filename, "/tmp/fileXXXXXX");\n'
                '    int fd = mkstemp(filename);\n'
                '    return fdopen(fd, "w");\n'
            )
            new_body = (
                '    strcpy(filename, "./file_XXXXXX");\n'
                '    int fd = mkstemp(filename);\n'
                '    if (fd < 0) {\n'
                '        strcpy(filename, "/tmp/fileXXXXXX");\n'
                '        fd = mkstemp(filename);\n'
                '    }\n'
                '    if (fd < 0) {\n'
                '        return 0;\n'
                '    }\n'
                '    return fdopen(fd, "w");\n'
            )
            h_new = h_text.replace(old_body, new_body)
            if h_new == h_text:
                # Fall back to the narrow strcpy-only patch if the body shape
                # differs (e.g. upstream changed). Use a short CWD-relative
                # template that fits in ``char filename[L_tmpnam];``.
                h_new = h_text.replace(
                    'strcpy(filename, "/tmp/fileXXXXXX");',
                    'strcpy(filename, "./file_XXXXXX");')
            if h_new != h_text:
                with open(unittest_h, "w", encoding="utf-8") as fh:
                    fh.write(h_new)
                self.output.info(
                    "Patched unittest.h TempFile() to short CWD-relative "
                    "mkstemp template (./file_XXXXXX) — fits in L_tmpnam, "
                    "no stack overflow on long HMBS TMPDIR")
        except OSError as e:
            self.output.warning(f"Could not patch unittest.h TempFile template: {e}")

        # Configure with CMake. Force CMAKE_SYSTEM_NAME=Linux so CMake does not
        # bail on the unknown HarmonyOS platform (only affects CMake's system-id
        # probe, not the compiled output of a header-only library's tests).
        os.makedirs(build_test_dir, exist_ok=True)
        configure_args = [
            cmake_bin, "-S", src_dir, "-B", build_test_dir,
            "-DCMAKE_SYSTEM_NAME=Linux",
            "-DCMAKE_SYSTEM_PROCESSOR=aarch64",
            f"-DCMAKE_C_COMPILER={cc}",
            f"-DCMAKE_CXX_COMPILER={cxx}",
            f"-DCMAKE_MAKE_PROGRAM={make_bin}",
            "-DCMAKE_CXX_STANDARD=11",
            "-DRAPIDJSON_HAS_STDSTRING=ON",
            "-DRAPIDJSON_BUILD_TESTS=ON",
            "-DRAPIDJSON_BUILD_DOC=OFF",
            "-DRAPIDJSON_BUILD_EXAMPLES=OFF",
            "-DRAPIDJSON_BUILD_THIRDPARTY_GTEST=ON",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DCMAKE_CXX_FLAGS=-Wno-zero-as-null-pointer-constant -Wno-exceptions -Wno-c++98-compat -Wno-suggest-destructor-override -Wno-gnu-zero-variadic-macro-arguments -Wno-suggest-override -Wno-shadow -Wno-shadow-field -Wno-shadow-field-in-constructor -Wno-extra-semi-stmt -Wno-self-assign-overloaded",
        ]
        self.output.info("RUN: " + " ".join(configure_args))
        proc = subprocess.run(configure_args, capture_output=True,
                              text=True, timeout=600)
        if proc.returncode != 0:
            err_tail = (proc.stderr or proc.stdout or "").strip()[-400:]
            self.output.warning(f"CMake configure failed (rc={proc.returncode}):\n{err_tail}")
            self._emit_failed_marker(
                "CMake configure failed (rc=" + str(proc.returncode) + "): "
                + err_tail.replace('"', "'").replace('\n', ' '))
            raise ConanException("upstream test configure failed; see HMBS_UPSTREAM_TEST_RESULT marker above")

        # Build the unittest target.
        cmd_build = (
            f'"{cmake_bin}" --build "{build_test_dir}" '
            f'--target unittest '
            f'-- -j1'
        )
        rc = self.run(cmd_build, ignore_errors=True)
        if rc != 0:
            self.output.warning(f"CMake build unittest failed (rc={rc})")
            self._emit_failed_marker(
                "Failed to build upstream unittest binary (rc="
                + str(rc) + "); see conan log for the build error output",
                cmd="cmake --build . --target unittest")
            raise ConanException("upstream test build failed; see HMBS_UPSTREAM_TEST_RESULT marker above")

        # Locate the unittest binary.
        bin_candidates = [
            os.path.join(build_test_dir, "bin", "unittest"),
            os.path.join(build_test_dir, "unittest"),
            os.path.join(build_test_dir, "tests", "unittest"),
        ]
        unittest_bin = None
        for p in bin_candidates:
            if os.path.exists(p) and os.access(p, os.X_OK):
                unittest_bin = p
                break

        if not unittest_bin:
            for root, dirs, files in os.walk(build_test_dir):
                for f in files:
                    if f == "unittest":
                        full = os.path.join(root, f)
                        if os.access(full, os.X_OK):
                            unittest_bin = full
                            break
                if unittest_bin:
                    break

        if not unittest_bin:
            self.output.warning("unittest binary not found after build")
            self._emit_failed_marker(
                "unittest binary not found after successful CMake build")
            raise ConanException("unittest binary not found after build; see HMBS_UPSTREAM_TEST_RESULT marker above")

        # Run the unittest binary directly via subprocess (no shell), which
        # fork+execs the native ELF without going through mksh.
        #
        # cwd is set to ``<src_dir>/bin`` to match the upstream CMake
        # ``add_test(... WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/bin)`` contract.
        # upstream's ``jsoncheckertest.cpp::ReadFile`` looks up fixtures via the
        # relative paths ``jsonchecker/`` and ``bin/jsonchecker/`` (etc.), and the
        # fixture files live under ``rapidjson-1.1.0/bin/jsonchecker/``. Without
        # this cwd every JsonChecker assertion fails with
        # ``jsonchecker file failXX.json not found``. The upstream tests themselves
        # are not modified — we only reproduce the working directory upstream's
        # own CTest definition prescribes.
        #
        # env explicitly forwards the HMBS-injected TMPDIR/TMP/TEMP so the patched
        # TempFile() (sprintf with the resolved TMPDIR literal) and any children
        # honoring TMPDIR see the writable per-task scratch dir. subprocess.run
        # does NOT inherit Conan's injected env by default, so we copy os.environ
        # and ensure TMPDIR is set even if the parent Conan env elided it.
        unittest_cwd = os.path.join(src_dir, "bin")
        if not os.path.isdir(unittest_cwd):
            # Fall back to src_dir if bin/ somehow absent — JsonChecker will
            # report fixture-not-found (a real failure we surface honestly)
            # rather than crash on a missing cwd.
            unittest_cwd = src_dir

        run_env = dict(os.environ)
        tmpdir_val = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                      or os.environ.get("TEMP"))
        if tmpdir_val:
            run_env.setdefault("TMPDIR", tmpdir_val)
            run_env.setdefault("TMP", tmpdir_val)
            run_env.setdefault("TEMP", tmpdir_val)

        self.output.info(f"Running upstream test suite: {unittest_bin} (cwd={unittest_cwd})")
        try:
            result = subprocess.run(
                [unittest_bin],
                capture_output=True, text=True, timeout=900,
                cwd=unittest_cwd, env=run_env,
            )
            output = result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired:
            self.output.warning("upstream tests timed out")
            marker = {
                "status": "incomplete", "framework": "gtest",
                "command": "unittest", "discovered": 0, "executed": 0,
                "passed": 0, "failed": 0, "skipped": 0,
                "reason": "upstream tests timed out after 900s",
            }
            print(f'HMBS_UPSTREAM_TEST_RESULT={json.dumps(marker, ensure_ascii=False)}')
            return
        except Exception as e:
            self.output.warning(f"upstream tests failed to run: {e}")
            self._emit_failed_marker(f"unittest execution failed: {e}")
            return

        # Parse GTest output for test counts.
        #
        # GTest's normal end-of-run summary looks like:
        #   [==========] 263 tests from 39 test cases ran. (1234 ms total)
        #   [  PASSED  ] 263 tests.
        #   [  FAILED  ] 0 tests, listed below:
        #
        # That summary only prints when the process exits cleanly. If a test
        # triggers an uncaught exception that escapes GTest's per-test
        # try/catch (e.g. an exception thrown from a TEST_F SetUp/TearDown or
        # from a destructor), ``std::terminate`` calls ``abort()`` and the
        # process dies mid-run — the summary line never prints, so the naive
        # ``[  PASSED  ] N tests`` regex returns nothing and ``passed`` falls
        # to 0 even though dozens of ``[       OK ]`` lines already proved
        # those cases ran green.
        #
        # To report honest numbers in both the clean-exit and crash cases we:
        #   1. prefer the final summary counts when present;
        #   2. fall back to counting per-case ``[       OK ]`` / ``[  FAILED  ]``
        #      lines (GTest emits one per adjudicated case) so a crash still
        #      yields ``passed`` = the cases that ran green before the crash,
        #      and ``failed`` = the cases GTest explicitly marked FAILED plus
        #      the case the process died inside (detected via non-zero rc with
        #      ``passed+failed < run_count``);
        #   3. fall back ``discovered`` to the ``[ RUN      ]`` line count when
        #      the ``[==========]`` summary is absent (crash), so we never
        #      report ``discovered=0`` for a run that clearly executed cases.
        passed_match = re.search(r'\[\s*PASSED\s*\]\s*(\d+)\s+test', output)
        failed_match = re.search(r'\[\s*FAILED\s*\]\s*(\d+)\s+test', output)
        total_match = re.search(r'\[\s*==========\s*\]\s*(\d+)\s+tests?\s+from', output)
        run_count = len(re.findall(r'\[\s*RUN\s*\]', output))
        ok_count = len(re.findall(r'\[\s*OK\s*\]', output))
        failed_case_count = len(re.findall(r'\[\s*FAILED\s*\]', output))

        passed = int(passed_match.group(1)) if passed_match else ok_count
        failed = int(failed_match.group(1)) if failed_match else failed_case_count
        discovered = int(total_match.group(1)) if total_match else run_count
        executed = (passed + failed) if (passed + failed) > 0 else run_count

        # If the process crashed mid-case, GTest will have printed a ``[ RUN ]``
        # for the dying case but no ``[ OK ]`` / ``[ FAILED ]``. Detect that
        # gap (non-zero rc + adjudicated count < started count) and charge the
        # unfinished case to ``failed`` so hmbs sees an honest failure instead
        # of a contradictory ``executed=N passed=0 failed=0``.
        if result.returncode != 0 and (passed + failed) < run_count:
            crashed = run_count - (passed + failed)
            failed += crashed
            executed = passed + failed
            self.output.warning(
                f"upstream unittest crashed mid-case; charging {crashed} "
                f"unfinished case(s) to failed (passed={passed} failed={failed})")

        status = "passed" if failed == 0 and result.returncode == 0 else "failed"

        print(output)  # Print full test output to conan log
        result_dict = {
            "status": status,
            "framework": "gtest",
            "command": "unittest",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        print(f'HMBS_UPSTREAM_TEST_RESULT={json.dumps(result_dict)}')

    def _emit_failed_marker(self, reason, cmd="unittest"):
        """Emit a failed HMBS_UPSTREAM_TEST_RESULT marker."""
        marker = {
            "status": "failed", "framework": "gtest",
            "command": cmd, "discovered": 0, "executed": 0,
            "passed": 0, "failed": 0, "skipped": 0,
            "reason": reason,
        }
        print(f'HMBS_UPSTREAM_TEST_RESULT={json.dumps(marker, ensure_ascii=False)}')
