#!/usr/bin/env python3
"""Conan recipe for libyang 3.13.6 — CMake build system."""
import glob
import json
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibyangConan(ConanFile):
    name = "libyang"
    version = "3.13.6"
    description = "YANG data modeling language parser and toolkit"
    license = "BSD-3-Clause"
    homepage = "https://github.com/CESNET/libyang"
    url = "https://github.com/CESNET/libyang"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libyang is validated only for Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # PCRE2 (>= 10.21) is mandatory: upstream find_package(PCRE2 REQUIRED).
        # Pin the ohpcd-only OHOS-adapted 10.45.1.1 (Autotools, no zlib/bzip2
        # closure). pcre2/10.40 resolves to the conancenter recipe whose
        # with_zlib/with_bzip2 defaults pull zlib+bzip2; conancenter bzip2 is
        # CMake-based and fails on OHOS ("System is unknown to cmake" +
        # read-only /tmp), breaking `conan create --build=missing` before
        # libyang itself builds. 10.45.1.1 exists only in ohpcd (published),
        # so Conan is forced onto the OHOS recipe with --disable-pcre2grep
        # equivalents and zero transitive deps.
        # tree_data.h includes <pcre2.h>: consumers link only
        # libyang::libyang, so propagate headers+libs transitively
        # (Conan 2 defaults do not); without this test_package fails
        # with 'pcre2.h file not found' (preflight 19:51).
        self.requires("pcre2/10.45.1.1", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # CMocka drives the upstream CTest suite (tests/utests, cmocka asserts).
        # Without it upstream silently sets ENABLE_TESTS=OFF, so require it to
        # guarantee the suite is really built and executed (same approach as
        # authselect/1.7.1).
        self.test_requires("cmocka/2.0.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # E092: CMake 4.x has no Platform/HarmonyOS module, so the default
        # Conan mapping (CMAKE_SYSTEM_NAME=HarmonyOS) fails configure with
        # "System is unknown to cmake" + a broken CMAKE_C_COMPILER check.
        # OHOS runs the HongMeng Linux-compatible kernel on aarch64, so map
        # the target to Linux/aarch64 (same fix as cmocka/2.0.2, zxc/0.9.1,
        # easyloggingpp/9.97.1). Linux hosts keep the default mapping.
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # HMBS readonly-/tmp hardening + pinned-compiler fallback (see the
        # _forward_hmbs_tmpdir / _fallback_missing_compilers helpers below).
        # Healthy runners: conf compilers exist -> zero behaviour change.
        self._forward_hmbs_tmpdir()
        self._fallback_missing_compilers(tc)
        # Upstream declares cmake_minimum_required(VERSION 2.8.12...3.28.1),
        # which CMake 4.x rejects; same fix as libyaml/0.2.5.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["BUILD_SHARED_LIBS"] = (
            "ON" if self.options.shared else "OFF"
        )
        # Upstream forces ENABLE_TESTS=OFF for static builds (the utest
        # binaries link $<TARGET_OBJECTS:yangobj>, which only exists for the
        # shared build). Mirror that instead of fighting it.
        tc.cache_variables["ENABLE_TESTS"] = (
            "ON" if self.options.shared else "OFF"
        )
        tc.cache_variables["ENABLE_VALGRIND_TESTS"] = "OFF"
        tc.cache_variables["ENABLE_COVERAGE"] = "OFF"
        tc.cache_variables["ENABLE_FUZZ_TARGETS"] = "OFF"
        tc.variables["ENABLE_TOOLS"] = True
        # Keep installed layout Conan-friendly (ohos.toolchain defaults the
        # 64-bit lib dir to lib64/; same fix as lerc/4.2.0).
        tc.cache_variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # The in-tree FindPCRE2/FindCMocka modules only search fixed system
        # paths, so point them at the Conan dependencies explicitly (same
        # idea as libevent/2.1.13 ZLIB_INCLUDE_DIR/ZLIB_LIBRARY).
        # Round-5 fix: singular cache entries alone are not enough —
        # upstream does `unset(PCRE2_LIBRARY CACHE)` before find_package, and
        # both modules gate on plural vars / CMOCKA_ROOT_DIR, so the previous
        # preflight configured OK yet compiled with `pcre2.h file not found`
        # and reported `Disabling tests because of missing CMocka`. Feed the
        # modules through their documented search inputs as well.
        pcre2_include, pcre2_library = self._dep_layout(
            "pcre2", "pcre2.h", ["pcre2-8"]
        )
        tc.cache_variables["PCRE2_INCLUDE_DIR"] = pcre2_include.replace("\\", "/")
        tc.cache_variables["PCRE2_LIBRARY"] = pcre2_library.replace("\\", "/")
        # Round-6 bypass: the in-tree FindPCRE2 short-circuits ONLY on the
        # plural pair (if(PCRE2_LIBRARIES AND PCRE2_INCLUDE_DIRS) -> FOUND),
        # while CMakeLists does unset(PCRE2_LIBRARY CACHE) before
        # find_package, wiping the singular entry every configure. Pre-seed
        # the plural pair so the module early-exits with our Conan paths and
        # never runs its hardcoded /usr search (which is where the previous
        # round's "configured OK yet pcre2.h not found" came from: the search
        # found nothing usable, PCRE2_INCLUDE_DIRS stayed empty, but REQUIRED
        # still passed via a stale cache entry while include_directories()
        # received an empty dir).
        tc.cache_variables["PCRE2_INCLUDE_DIRS"] = pcre2_include.replace("\\", "/")
        tc.cache_variables["PCRE2_LIBRARIES"] = pcre2_library.replace("\\", "/")
        cmocka_include, cmocka_library = self._dep_layout(
            "cmocka", "cmocka.h", ["cmocka"]
        )
        tc.cache_variables["CMOCKA_INCLUDE_DIR"] = cmocka_include.replace("\\", "/")
        tc.cache_variables["CMOCKA_LIBRARY"] = cmocka_library.replace("\\", "/")
        # Round-6 bypass: FindCMocka has no early-exit and its library search
        # is broken by construction (find_library PATHS
        # ${CMOCKA_ROOT_DIR}/include -- libraries are never under include/),
        # so CMOCKA_ROOT_DIR alone can never yield CMOCKA_LIBRARY (hence the
        # persistent "Disabling tests because of missing CMocka"). CMake
        # find_* commands skip the search when the cache variable already
        # exists, so pre-seeding CMOCKA_LIBRARY/CMOCKA_LIBRARIES makes the
        # broken PATHS irrelevant and lets
        # find_package_handle_standard_args succeed on real Conan paths.
        tc.cache_variables["CMOCKA_LIBRARIES"] = cmocka_library.replace("\\", "/")
        pcre2_root = self.dependencies["pcre2"].package_folder.replace("\\", "/")
        cmocka_root = self.dependencies["cmocka"].package_folder.replace("\\", "/")
        tc.cache_variables["CMOCKA_ROOT_DIR"] = cmocka_root
        tc.cache_variables["CMAKE_INCLUDE_PATH"] = ";".join(
            [pcre2_include.replace("\\", "/"), cmocka_include.replace("\\", "/")]
        )
        tc.cache_variables["CMAKE_LIBRARY_PATH"] = ";".join(
            [
                os.path.dirname(pcre2_library).replace("\\", "/"),
                os.path.dirname(cmocka_library).replace("\\", "/"),
            ]
        )
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join([pcre2_root, cmocka_root])
        self.output.info(f"HMBS dep roots: pcre2={pcre2_root} cmocka={cmocka_root}")
        tc.generate()
        # Round-4 delivery fix: the previous round proved tc.variables alone
        # cannot move the compiler — the generated conan_toolchain.cmake still
        # baked /data/service/hnp/bin/clang and CMake honoured it. Patch the
        # emitted toolchain file(s) in place so the stale absolute path never
        # reaches the compiler check (aggregated-exp #1 consumer-side sync).
        self._patch_toolchain_compilers()
        VirtualRunEnv(self).generate()

    def _hmbs_toolchain_files(self):
        roots = []
        for attr in ("generators_folder", "build_folder"):
            try:
                root = getattr(self, attr, None)
            except Exception:
                root = None
            if root and os.path.isdir(root) and root not in roots:
                roots.append(root)
        found = []
        for root in roots:
            for dirpath, _, filenames in os.walk(root):
                if "conan_toolchain.cmake" in filenames:
                    found.append(os.path.join(dirpath, "conan_toolchain.cmake"))
        return sorted(set(found))

    def _patch_toolchain_compilers(self):
        c_found = getattr(self, "_hmbs_c_compiler", "") or os.environ.get("CC", "")
        cpp_found = getattr(self, "_hmbs_cxx_compiler", "") or os.environ.get("CXX", "")
        if not c_found and not cpp_found:
            return
        compilers = (
            self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            or {}
        )
        replacements = []
        for stale, fresh in (
            (compilers.get("c", "") or "", c_found),
            (compilers.get("cpp", "") or "", cpp_found),
        ):
            if stale and fresh and stale != fresh:
                replacements.append((stale, fresh))
        if not replacements:
            return
        for path in self._hmbs_toolchain_files():
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as stream:
                    text = stream.read()
            except OSError:
                continue
            patched = text
            for stale, fresh in replacements:
                if stale in patched:
                    patched = patched.replace(stale, fresh)
            if patched != text:
                try:
                    with open(path, "w", encoding="utf-8") as stream:
                        stream.write(patched)
                    self.output.info(f"HMBS toolchain patch: {path}")
                except OSError as exc:
                    self.output.warning(f"HMBS toolchain patch failed for {path}: {exc}")

    def _cmake_configure_variables(self):
        variables = {}
        c_found = getattr(self, "_hmbs_c_compiler", "") or ""
        cpp_found = getattr(self, "_hmbs_cxx_compiler", "") or ""
        if not c_found:
            c_found = os.environ.get("CC", "")
        if not cpp_found:
            cpp_found = os.environ.get("CXX", "")
        if c_found and os.path.isfile(c_found) and self._compiler_usable(c_found, "c"):
            variables["CMAKE_C_COMPILER"] = c_found
        if cpp_found and os.path.isfile(cpp_found) and self._compiler_usable(cpp_found, "c++"):
            variables["CMAKE_CXX_COMPILER"] = cpp_found
        return variables

    def build(self):
        apply_conandata_patches(self)
        # Round-9 enforcement (differs from round-7/8 static patch, which
        # aborted in apply_conandata_patches with "source file is
        # different"): conandata.yml now carries no patches; guarantee the
        # FindCMocka fix purely via the tolerant build-time rewrite below,
        # and log which sub-fix actually fired.
        self._ensure_findcmocka_fix()
        # Round-10 caller bypass (differs from round-9's Find-module-only
        # fix, which still reported "Disabling tests because of missing
        # CMocka"): neutralize the find_package(CMocka) caller itself with
        # concrete Conan paths so the fragile module search/version logic
        # can no longer switch ENABLE_TESTS off.
        self._ensure_cmocka_caller_fix()
        # Round-11 headers fix (differs from round-9/10 CMocka routes):
        # compat/check_includes.sh needs bash, absent on device.
        self._ensure_check_includes_posix()
        # Re-assert the writable temp root in this phase as well: build()
        # spawns CMake compiler probes that otherwise fall back to /tmp.
        # generate()-time script already persists it; here only touch
        # os.environ (save_script belongs to generate()).
        _tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if not _tmp:
            _tmp = os.path.join(self.build_folder, "hmbs-tmp")
        try:
            os.makedirs(_tmp, exist_ok=True)
        except OSError:
            pass
        for _var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_var] = _tmp
        # Toolchain patch must precede the first configure so CMake never
        # sees the stale pinned path (round-4 channel, replaces the
        # variables-only attempt that the preflight log proved ineffective).
        self._patch_toolchain_compilers()
        cmake = CMake(self)
        cmake.configure(variables=self._cmake_configure_variables() or None)
        cmake.build()

        if not can_run(self):
            self.output.warning(
                "The target cannot run on this build host; upstream tests "
                "must run on a native worker."
            )
            return

        if self.settings.os == "OHOS":
            self._sign_build_artifacts()
        if self.options.shared:
            self._run_upstream_tests()
        else:
            self.output.warning(
                "Upstream CTest suite requires the shared build (upstream "
                "forces ENABLE_TESTS=OFF for static); consumer validation "
                "still runs via test_package."
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # Persist the real-device upstream result so test_package can re-emit
        # HMBS_UPSTREAM_TEST_RESULT even when build() is skipped by the cache
        # (same convention as boxes/2.3.1).
        copy(
            self,
            "upstream_test_result.json",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "res"),
        )
        if self.settings.os == "OHOS":
            artifacts = glob.glob(
                os.path.join(self.package_folder, "lib", "**", "*.so*"),
                recursive=True,
            )
            artifacts.extend(
                glob.glob(os.path.join(self.package_folder, "bin", "*"))
            )
            self._sign_paths(artifacts, required=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libyang")
        self.cpp_info.set_property("cmake_target_name", "libyang::libyang")
        self.cpp_info.set_property("pkg_config_name", "libyang")
        self.cpp_info.libs = ["yang"]
        self.cpp_info.bindirs = ["bin"]
        # tree_data.h includes <pcre2.h>, so consumers need the transitive
        # include/lib even though they only link libyang::libyang.
        self.cpp_info.requires = ["pcre2::pcre2-8"]
        if self.settings.os in ("Linux", "OHOS"):
            # Upstream links m + Threads into libyang; consumers inherit them.
            self.cpp_info.system_libs = ["m", "pthread"]

    def _ctest_dir(self):
        """Resolve the CMake binary dir that owns the full test set.

        Previous round used the deepest CTestTestfile.cmake match, which
        landed on the leaf .../tests/yanglint (0 tests there) and produced
        "No upstream tests discovered". Different strategy this round:
        collect every dir holding CTestTestfile.cmake under the build
        folder, probe each with `ctest --show-only=json-v1`, and use the
        one with the most tests (the top-level binary dir,
        .../b/build/Release, owns all 60). Falls back to self.build_folder.
        """
        import json as _json

        base = self.build_folder or "."
        ctest = shutil.which("ctest") or "ctest"
        candidates = []
        try:
            for dirpath, _, filenames in os.walk(base):
                if "CTestTestfile.cmake" in filenames:
                    candidates.append(dirpath)
        except OSError:
            pass
        if not candidates:
            chosen = base
            try:
                self.output.info(f"HMBS ctest dir: {chosen} (fallback, no CTestTestfile)")
            except Exception:
                pass
            return chosen
        # Shallow first for stable logs, but the decision is by test count.
        candidates = sorted(set(candidates), key=len)
        best_dir = candidates[0]
        best_count = -1
        for cand in candidates:
            try:
                proc = subprocess.run(
                    [ctest, "--show-only=json-v1"],
                    cwd=cand,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=60,
                )
                count = len(_json.loads(proc.stdout).get("tests", [])) if proc.returncode == 0 else -1
            except Exception:
                count = -1
            try:
                self.output.info(f"HMBS ctest probe: {cand} -> {count} tests")
            except Exception:
                pass
            if count > best_count:
                best_count = count
                best_dir = cand
        try:
            self.output.info(f"HMBS ctest dir: {best_dir} ({best_count} tests)")
        except Exception:
            pass
        return best_dir

    def _run_upstream_tests(self):
        """Run the upstream CTest suite on the real device and emit machine evidence."""
        ctest = shutil.which("ctest") or "ctest"
        ctest_dir = self._ctest_dir()
        listing = subprocess.run(
            [ctest, "--show-only=json-v1"],
            cwd=ctest_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if listing.returncode:
            raise ConanException(
                f"ctest JSON listing failed ({listing.returncode}): {listing.stderr}"
            )
        try:
            listed = json.loads(listing.stdout).get("tests", [])
        except ValueError as exc:
            raise ConanException(f"ctest JSON listing unparseable: {exc}")
        discovered_names = [t.get("name", "") for t in listed]
        discovered = len(discovered_names)
        if discovered == 0:
            raise ConanException(
                "No upstream tests discovered; refusing to emit an empty pass"
            )
        self.output.info(
            f"HMBS ctest discovered={discovered}: {','.join(discovered_names[:8])}..."
        )
        test_tmp = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(test_tmp, exist_ok=True)
        loader_environment = Environment()
        loader_environment.define("TMPDIR", test_tmp)
        loader_environment.define("TMP", test_tmp)
        loader_environment.define("TEMP", test_tmp)
        loader_environment.prepend_path("LD_LIBRARY_PATH", ctest_dir)
        loader_environment.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(ctest_dir, "lib")
        )
        loader_environment.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(ctest_dir, "tests")
        )
        # Keep the base build folder on the loader path as well (covers
        # cmake_layout variants where libs land one level up).
        loader_environment.prepend_path("LD_LIBRARY_PATH", self.build_folder)
        # Round-11 headers fix: the upstream `headers` test execs
        # compat/check_includes.sh via `#!/usr/bin/env bash`, but the
        # preflight device has no bash (`env: exec bash: No such file or
        # directory`, test #57). Provide a PATH shim so `env bash`
        # resolves (symlink to /bin/sh; no chmod needed) alongside the
        # POSIX rewrite of the script itself (see
        # _ensure_check_includes_posix). Only the interpreter line and
        # the brace-glob are touched; no check is removed.
        self._ensure_bash_shim(test_tmp)
        loader_environment.prepend_path("PATH", test_tmp)
        with VirtualRunEnv(self).vars().apply(), loader_environment.vars(
            self
        ).apply():
            proc = subprocess.run(
                [ctest, "--output-on-failure", "--no-tests=error"],
                cwd=ctest_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        # Keep the raw framework output in the log: it is the audit trail the
        # PR pass-rate numbers are transcribed from.
        print(proc.stdout, flush=True)
        passed, failed, skipped, found_names = self._parse_ctest_output(proc.stdout)
        # Diagnose discovery-vs-execution drift by name (not just counts):
        # the previous round showed discovered=60 executed=51 with no names,
        # leaving the 9 missing tests unidentifiable. Log the exact missing
        # set so the next round can target the root cause instead of guessing.
        found_set = set(found_names)
        missing = [n for n in discovered_names if n not in found_set]
        if missing:
            self.output.warning(
                f"HMBS ctest missing ({len(missing)}): {','.join(missing[:20])}"
            )
            # Retry each missing test in the same env and merge the results.
            # If the 9 first types
            # tests are flaky-missing (output truncation / runner quirk),
            # the retry recovers their real verdicts; if they are really
            # broken, each retry logs its explicit failure instead of a
            # bare count mismatch. No test is skipped or deleted.
            for name in list(missing):
                with VirtualRunEnv(self).vars().apply(), loader_environment.vars(
                    self
                ).apply():
                    retry = subprocess.run(
                        [ctest, "-R", f"^{name}$", "--output-on-failure"],
                        cwd=ctest_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        check=False,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )
                print(f"HMBS retry {name} exit={retry.returncode}\n{retry.stdout}", flush=True)
                r_passed, r_failed, r_skipped, r_found = self._parse_ctest_output(retry.stdout)
                passed += r_passed
                failed += r_failed
                skipped += r_skipped
                for found in r_found:
                    if found not in found_set:
                        found_set.add(found)
                        found_names.append(found)
            missing = [n for n in discovered_names if n not in found_set]
            if missing:
                self.output.warning(
                    f"HMBS ctest still missing ({len(missing)}): {','.join(missing[:20])}"
                )
                # Dump executable presence for the still-missing set so the
                # next round sees whether binaries exist / are executable.
                for name in missing[:20]:
                    for root, _, files in os.walk(ctest_dir):
                        if name in files:
                            full = os.path.join(root, name)
                            try:
                                st = os.stat(full)
                                self.output.info(
                                    f"HMBS missing binary: {full} size={st.st_size} mode={oct(st.st_mode)}"
                                )
                            except OSError as exc:
                                self.output.info(f"HMBS missing binary stat failed {full}: {exc}")
                            break
                    else:
                        self.output.info(f"HMBS missing binary not found under {ctest_dir}: {name}")
        executed = passed + failed
        if executed + skipped != discovered:
            raise ConanException(
                f"ctest accounting mismatch: discovered={discovered} "
                f"executed={executed} skipped={skipped} "
                f"missing=[{','.join(missing[:20])}] ctest_dir={ctest_dir}"
            )
        status = "passed" if (failed == 0 and executed > 0) else "failed"
        upstream = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure --no-tests=error",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        result_file = os.path.join(self.build_folder, "upstream_test_result.json")
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(upstream, f, ensure_ascii=False)
        print(
            f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(upstream, ensure_ascii=False)}",
            flush=True,
        )
        if proc.returncode != 0 or failed > 0:
            raise ConanException(
                f"libyang upstream tests failed: {failed} FAIL, {passed} PASS "
                f"(ctest exit={proc.returncode})"
            )

    @staticmethod
    def _parse_ctest_output(output):
        """Classify every registered ctest case from its result line.

        Passing lines look like `` 3/56 Test  #3: utest_uint32 ... Passed``.
        Anything that is not an explicit pass (Failed/Timeout/Skipped/Not Run)
        must not be counted as passed: exit code 0 alone proves nothing.
        Any ``Test #`` line that is neither an explicit pass nor an
        explicit skip is a failure (covers ``***Failed``, ``***Timeout``,
        ``***Exception``, ``***Not Run`` variants and future labels), so
        every registered test is accounted exactly once.
        Returns (passed, failed, skipped, found_names).
        """
        import re

        passed = failed = skipped = 0
        found_names = []
        pattern = re.compile(r"Test\s+#\d+:\s+(\S+)")
        for line in output.splitlines():
            if "Test #" not in line:
                continue
            match = pattern.search(line)
            name = match.group(1) if match else ""
            # Strip trailing dots ctest appends for alignment.
            name = name.rstrip(".")
            if name:
                found_names.append(name)
            tail = line.split("Test #", 1)[-1]
            if "Passed" in line:
                passed += 1
            elif "Skipped" in tail or "Not Run" in line or "Disabled" in tail:
                skipped += 1
            else:
                # Failed / ***Failed / Timeout / Exception / Crash ...
                failed += 1
        return passed, failed, skipped, found_names

    def _forward_hmbs_tmpdir(self):
        """Redirect temp roots to the HMBS-provided writable TMPDIR.

        /tmp is read-only on the preflight device (preflight.sh mktemp
        failures); HMBS injects a task-private TMPDIR/TMP/TEMP. Persist it
        into a conanbuild env script so every build-step subprocess
        (including CMake's compiler-identification probes) inherits the
        writable root. Only the temp root is redirected; no test is
        skipped or deleted.
        """
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )
        if not tmpdir:
            tmpdir = os.path.join(self.build_folder, "hmbs-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmpdir
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.vars(self).save_script("hmbs_tmpdir")

    def _probe_clang(self, candidate):
        """Return True iff candidate runs and reports a clang version."""
        if not candidate or not os.path.isfile(candidate):
            return False
        if not os.access(candidate, os.X_OK):
            return False
        try:
            proc = subprocess.run(
                [candidate, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return proc.returncode == 0 and "clang" in proc.stdout.lower()

    def _probe_compile(self, candidate, lang):
        """Compile-only probe: --version may pass while real compilation fails.

        Previous round proved this: the conf clang answered --version (so no
        C fallback triggered) yet CMake still reported "identification is
        unknown". Probe with a header-free trivial source and -c (no link,
        no sysroot needed), forcing temp files into the HMBS-writable TMPDIR.
        """
        if not candidate or not os.path.isfile(candidate):
            return False
        if lang == "c++":
            source = "int main(){return 0;}\n"
            lang_flag = "c++"
            suffix = ".cpp"
        else:
            source = "int main(void){return 0;}\n"
            lang_flag = "c"
            suffix = ".c"
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, "hmbs-tmp")
        )
        try:
            os.makedirs(tmpdir, exist_ok=True)
            src = os.path.join(tmpdir, "hmbs-probe-%d-%s%s" % (os.getpid(), lang_flag, suffix))
            obj = src + ".o"
            with open(src, "w", encoding="utf-8") as stream:
                stream.write(source)
            env = dict(os.environ)
            env["TMPDIR"] = tmpdir
            env["TMP"] = tmpdir
            env["TEMP"] = tmpdir
            proc = subprocess.run(
                [candidate, "-x", lang_flag, "-c", src, "-o", obj],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
                check=False,
                env=env,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        try:
            return (
                proc.returncode == 0
                and os.path.isfile(obj)
                and os.path.getsize(obj) > 0
            )
        finally:
            for path in (src, obj):
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                except OSError:
                    pass

    def _compiler_usable(self, candidate, lang):
        """A conf compiler is usable only if it reports clang AND compiles."""
        if not self._probe_clang(candidate):
            self.output.info(
                "HMBS compiler probe: version check failed for %s" % (candidate or "<unset>")
            )
            return False
        if not self._probe_compile(candidate, lang):
            self.output.info(
                "HMBS compiler probe: compile check failed for %s" % candidate
            )
            return False
        return True

    def _discover_clang(self, names, lang):
        """Find a runnable compiler, PATH first (basename normalization).

        Experience 1 (libequihash/1.0.10): absolute conf paths are reduced
        to basenames and re-resolved via PATH so the HMBS-injected runnable
        prefix wins. Every candidate must pass both --version and a
        compile-only probe before it is accepted.
        """
        seen = set()
        # Explicit env overrides first (HMBS may export CC/CXX).
        for name in list(names) + [
            os.environ.get("CC", ""),
            os.environ.get("CXX", ""),
        ]:
            if not name or name in seen:
                continue
            seen.add(name)
            if os.path.isabs(name):
                if self._compiler_usable(name, lang):
                    return name
                continue
            if os.sep in name:
                continue
            found = shutil.which(name)
            if found and found not in seen:
                seen.add(found)
                if self._compiler_usable(found, lang):
                    return found
        # HMBS-known directories plus the conf compilers' own directories
        # (a runner may keep only one of clang/clang++ under a private prefix
        # such as .harmonybrew/bin, already on PATH for one but not the other).
        compilers = (
            self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            or {}
        )
        extra_dirs = [
            "/data/service/hnp/bin",
            "/usr/bin",
            "/usr/local/bin",
        ]
        for key in ("c", "cpp"):
            conf_dir = os.path.dirname(compilers.get(key, "") or "")
            if conf_dir and conf_dir not in extra_dirs:
                extra_dirs.append(conf_dir)
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        for directory in path_dirs + extra_dirs:
            if not directory:
                continue
            for name in names:
                if os.path.isabs(name) or os.sep in name:
                    continue
                candidate = os.path.join(directory, os.path.basename(name))
                if candidate not in seen:
                    seen.add(candidate)
                    if self._compiler_usable(candidate, lang):
                        return candidate
        return ""

    def _fallback_missing_compilers(self, tc):
        """Override baked-in compilers only when the conf path is unusable.

        The ohos-aarch64 profile pins tools.build:compiler_executables to an
        absolute path that is absent (or not really usable) on some preflight
        runners; the baked conan_toolchain.cmake then points
        CMAKE_C_COMPILER at a file that does not work and identification
        reports "unknown". Round 1 used a --version-only probe, but the
        failing runner answered --version for C yet still failed CMake
        identification, so round 2 requires a compile-only probe as well and
        resolves replacements PATH-first by basename (Experience 1). Round 3
        fixes the delivery channel: conf-derived compiler lines inside
        conan_toolchain.cmake override user tc.cache_variables, so the cache
        channel is ineffective for compiler keys (plutosvg #15 proved this
        for WORKS/TRY_COMPILE keys, #16 proved the CLI channel works).
        Compiler overrides therefore go through tc.variables (preset/CLI -D,
        plutosvg:501), which win over the toolchain file. Healthy runners
        (both conf compilers version-clean AND compile-clean) see zero
        change. Sibling lookup works in both directions so a runner
        with only clang++ visible still recovers clang.
        """
        compilers = (
            self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            or {}
        )
        c_conf = compilers.get("c", "") or ""
        cpp_conf = compilers.get("cpp", "") or ""
        c_ok = bool(c_conf) and self._compiler_usable(c_conf, "c")
        cpp_ok = bool(cpp_conf) and self._compiler_usable(cpp_conf, "c++")
        if c_ok and cpp_ok:
            self.output.info(f"HMBS compiler probe: conf compilers runnable ({c_conf})")
            return
        if not c_ok:
            self.output.info(
                f"HMBS compiler probe: C conf unusable ({c_conf or '<unset>'})"
            )
        if not cpp_ok:
            self.output.info(
                f"HMBS compiler probe: CXX conf unusable ({cpp_conf or '<unset>'})"
            )
        c_found = "" if c_ok else self._discover_clang(["clang", "cc"], "c")
        cpp_found = "" if cpp_ok else self._discover_clang(["clang++", "c++"], "c++")
        # Bidirectional sibling recovery: a private prefix may expose only
        # one of the two names (last round: CXX fell back to
        # .harmonybrew/bin/clang++ while C stayed on the stale conf path).
        # Siblings must also pass the compile probe, not just --version.
        if not c_found and cpp_found:
            sibling = os.path.join(os.path.dirname(cpp_found), "clang")
            if self._compiler_usable(sibling, "c"):
                c_found = sibling
            else:
                sibling_cc = os.path.join(os.path.dirname(cpp_found), "cc")
                if self._compiler_usable(sibling_cc, "c"):
                    c_found = sibling_cc
        if not cpp_found and c_found:
            sibling = os.path.join(os.path.dirname(c_found), "clang++")
            if self._compiler_usable(sibling, "c++"):
                cpp_found = sibling
        if not c_ok and c_found:
            # Preset/CLI channel (tc.variables), never tc.cache_variables:
            # conan_toolchain.cmake re-emits the conf compiler after user
            # cache entries, so the cache channel cannot move the compiler
            # (this round's log proved it: fallback printed yet CMake still
            # saw /data/service/hnp/bin/clang). -D via tc.variables wins
            # over the toolchain file (plutosvg:501, cryptokit/faudio CLI).
            # Round-4 note: that CLI-via-preset channel alone still lost, so
            # the value is also persisted for the post-generate toolchain
            # patch plus the build()-time -D override (see generate/build).
            tc.variables["CMAKE_C_COMPILER"] = c_found
            os.environ["CC"] = c_found
            self._hmbs_c_compiler = c_found
            self.output.info(f"HMBS compiler fallback: C {c_conf or '<unset>'} -> {c_found}")
        if not cpp_ok and cpp_found:
            tc.variables["CMAKE_CXX_COMPILER"] = cpp_found
            os.environ["CXX"] = cpp_found
            self._hmbs_cxx_compiler = cpp_found
            self.output.info(
                f"HMBS compiler fallback: CXX {cpp_conf or '<unset>'} -> {cpp_found}"
            )
        if (not c_ok and c_found) or (not cpp_ok and cpp_found):
            env = Environment()
            if not c_ok and c_found:
                env.define("CC", c_found)
            if not cpp_ok and cpp_found:
                env.define("CXX", cpp_found)
            env.vars(self).save_script("hmbs_compilers")
        if (not c_ok and not c_found) or (not cpp_ok and not cpp_found):
            raise ConanInvalidConfiguration(
                "HMBS compiler probe: no runnable clang found "
                f"(conf c={c_conf or '<unset>'} cpp={cpp_conf or '<unset>'}; "
                "PATH discovery failed). This is an environment fault, not a "
                "recipe bug."
            )

    def _dep_layout(self, ref, header, lib_names):
        """Locate a dependency's header and linkable library file."""
        dependency = self.dependencies[ref]
        include_dirs = list(dependency.cpp_info.includedirs or ["include"])
        library_dirs = list(dependency.cpp_info.libdirs or ["lib"])
        library_names = list(dependency.cpp_info.libs or lib_names)

        def absolute(path):
            return (
                path
                if os.path.isabs(path)
                else os.path.join(dependency.package_folder, path)
            )

        header_dir = next(
            (
                absolute(path)
                for path in include_dirs
                if os.path.isfile(os.path.join(absolute(path), header))
            ),
            "",
        )
        suffixes = (".a", ".so", ".dylib", ".lib", ".dll.a")
        filenames = [f"lib{name}{suffix}" for name in library_names for suffix in suffixes]
        filenames += [f"{name}{suffix}" for name in library_names for suffix in suffixes]
        library_file = next(
            (
                os.path.join(absolute(directory), filename)
                for directory in map(absolute, library_dirs)
                for filename in filenames
                if os.path.isfile(os.path.join(absolute(directory), filename))
            ),
            "",
        )
        if not header_dir or not library_file:
            raise ConanInvalidConfiguration(
                f"{ref} dependency must provide {header} and a linkable library"
            )
        return header_dir, library_file

    def _ensure_findcmocka_fix(self):
        """Enforce the FindCMocka repair in the unpacked source (round 9).

        Round 8 proved the static conandata patch channel itself is
        fragile: conan reported "source file is different" and aborted in
        apply_conandata_patches before any compilation (patch context
        mismatch on CMakeModules/FindCMocka.cmake). This round drops the
        static patch entirely (conandata.yml carries no patches) and keeps
        ONLY this build-time rewrite, implemented tolerantly: CRLF
        normalized, lib-path fix scoped to the find_library block, and the
        FindPCRE2-style early-exit guard injected by anchor strings rather
        than an exact whole-block match. Idempotent; logs which channel
        delivered the fix.
        """
        path = os.path.join(self.source_folder, "CMakeModules", "FindCMocka.cmake")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as stream:
                text = stream.read()
        except OSError as exc:
            self.output.warning(f"HMBS FindCMocka check skipped: {exc}")
            return
        # Normalize CRLF so tarball/Windows checkouts compare identically.
        patched = text.replace("\r\n", "\n").replace("\r", "\n")
        # 1) Library search fix, scoped to the find_library block only (the
        # find_path block for cmocka.h correctly searches include/).
        marker = "find_library(CMOCKA_LIBRARY"
        idx = patched.find(marker)
        if idx != -1 and "${CMOCKA_ROOT_DIR}/lib" not in patched[idx:idx + 2000]:
            head, tail = patched[:idx], patched[idx:]
            old_single = "${CMOCKA_ROOT_DIR}/include"
            new_triple = (
                "${CMOCKA_ROOT_DIR}/lib\n"
                "        ${CMOCKA_ROOT_DIR}/lib64\n"
                "        ${CMOCKA_ROOT_DIR}/include"
            )
            if old_single in tail:
                tail = tail.replace(old_single, new_triple, 1)
                patched = head + tail
                self.output.info("HMBS FindCMocka fixup: library PATHS corrected (build-time)")
        # 2) FindPCRE2-style cache early-exit (mirrors the proven PCRE2
        # bypass): when the recipe pre-seeded CMOCKA_LIBRARIES +
        # CMOCKA_INCLUDE_DIR, skip the fixed-path search entirely.
        if "set(CMOCKA_FOUND TRUE)" not in patched:
            head_old = "find_path(CMOCKA_INCLUDE_DIR"
            head_new = (
                "if(CMOCKA_LIBRARIES AND CMOCKA_INCLUDE_DIR)\n"
                "    # Seeded by the Conan recipe from its cmocka package: skip the\n"
                "    # fixed-path search below (mirrors FindPCRE2's early-exit).\n"
                "    set(CMOCKA_FOUND TRUE)\n"
                "    set(CMocka_FOUND TRUE)\n"
                "else()\n"
                "find_path(CMOCKA_INCLUDE_DIR"
            )
            tail_old = "mark_as_advanced(CMOCKA_INCLUDE_DIR CMOCKA_LIBRARIES)"
            if head_old in patched and tail_old in patched:
                patched = patched.replace(head_old, head_new, 1)
                patched = patched.replace(tail_old, tail_old + "\nendif()", 1)
                self.output.info("HMBS FindCMocka fixup: cache early-exit guard added (build-time)")
        if patched != text.replace("\r\n", "\n").replace("\r", "\n"):
            with open(path, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(patched)
        else:
            self.output.info(
                "HMBS FindCMocka check: source already carries the fix"
            )

    def _ensure_cmocka_caller_fix(self):
        """Bypass find_package(CMocka) at the caller (round 10).

        Round 9 fixed only CMakeModules/FindCMocka.cmake, yet preflight
        still printed "Disabling tests because of missing CMocka": the
        module search stays subject to cross find-root restrictions and
        the `find_package(CMocka 1.0.1)` version handshake, so any residual
        miss switches ENABLE_TESTS off before a single test is registered.
        This round takes a different route and patches the caller
        (top-level CMakeLists.txt) with concrete Conan absolute paths, so
        the fragile search can no longer veto the suite. Idempotent and
        logged; the Find-module fix above is kept as fallback.
        """
        try:
            cmocka_include, cmocka_library = self._dep_layout(
                "cmocka", "cmocka.h", ["cmocka"]
            )
        except ConanInvalidConfiguration as exc:
            self.output.warning(f"HMBS CMocka caller fix skipped: {exc}")
            return
        cmocka_include = cmocka_include.replace("\\", "/")
        cmocka_library = cmocka_library.replace("\\", "/")
        path = os.path.join(self.source_folder, "CMakeLists.txt")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as stream:
                text = stream.read()
        except OSError as exc:
            self.output.warning(f"HMBS CMocka caller fix skipped: {exc}")
            return
        norm = text.replace("\r\n", "\n").replace("\r", "\n")
        if "HMBS CMocka caller bypass" in norm:
            self.output.info("HMBS CMocka caller fix: already applied")
            return
        anchor = "find_package(CMocka 1.0.1)"
        if anchor not in norm:
            self.output.warning("HMBS CMocka caller fix skipped: anchor not found")
            return
        bypass = (
            "# HMBS CMocka caller bypass: Conan provides cmocka; skip the\n"
            "    # fragile FindCMocka search/version handshake (cross find-root\n"
            "    # restrictions) and use absolute Conan paths directly.\n"
            f"    set(CMOCKA_INCLUDE_DIR \"{cmocka_include}\" CACHE PATH \"\" FORCE)\n"
            f"    set(CMOCKA_LIBRARIES \"{cmocka_library}\" CACHE FILEPATH \"\" FORCE)\n"
            f"    set(CMOCKA_LIBRARY \"{cmocka_library}\" CACHE FILEPATH \"\" FORCE)\n"
            "    set(CMOCKA_FOUND TRUE)\n"
            "    set(CMocka_FOUND TRUE)\n"
            "    # HMBS: original find_package(CMocka 1.0.1) skipped on purpose -\n"
            "    # re-running the Find module would overwrite CMOCKA_FOUND via\n"
            "    # find_package_handle_standard_args and switch ENABLE_TESTS off.\n"
        )
        patched = norm.replace(anchor, bypass, 1)
        with open(path, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(patched)
        self.output.info(
            f"HMBS CMocka caller fix: ENABLE_TESTS pinned ON with {cmocka_library}"
        )

    def _ensure_check_includes_posix(self):
        """Make compat/check_includes.sh runnable without bash (round 11).

        The upstream `headers` test execs this script via
        `#!/usr/bin/env bash`; the preflight device has no bash
        (`env: exec bash: No such file or directory`). The script body
        is POSIX except for the brace glob `--include=\\*.{c,h}`, which
        relies on bash brace expansion: under /bin/sh grep receives the
        literal pattern `*.{c,h}`, matches nothing, and the test would
        pass vacuously (empty fixture vs empty expectation). Rewrite to
        `#!/bin/sh` plus two explicit `--include` flags so the same
        compat.h checks really run under the device shell. Idempotent.
        """
        path = os.path.join(self.source_folder, "compat", "check_includes.sh")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as stream:
                text = stream.read()
        except OSError as exc:
            self.output.warning(f"HMBS check_includes fix skipped: {exc}")
            return
        norm = text.replace("\r\n", "\n").replace("\r", "\n")
        patched = norm
        if patched.startswith("#!/usr/bin/env bash"):
            patched = "#!/bin/sh" + patched[len("#!/usr/bin/env bash"):]
        # Expand the bash-only brace glob into two portable flags.
        # Keep the backslash escape (\"--include=\\*.c\"): without it /bin/sh
        # would glob-expand *.c against the cwd before grep sees it, and the
        # test would pass vacuously on an empty file list.
        if "--include=\\*.{c,h}" in patched:
            patched = patched.replace(
                "--include=\\*.{c,h}",
                "--include=\\*.c --include=\\*.h",
            )
        if patched != norm:
            with open(path, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(patched)
            self.output.info("HMBS check_includes fix: bashisms removed (POSIX sh)")
        else:
            self.output.info("HMBS check_includes check: already POSIX")

    def _ensure_bash_shim(self, directory):
        """Provide a `bash` name resolving to the device shell (round 11).

        `#!/usr/bin/env bash` fails when PATH has no bash. Prefer a real
        bash if one exists on PATH/known prefixes (keeps exact upstream
        semantics); otherwise symlink `bash` -> `/bin/sh` inside the
        writable test tmp dir (symlink needs no chmod, which the device
        forbids). The caller prepends `directory` to PATH. Idempotent.
        """
        bash_path = os.path.join(directory, "bash")
        if os.path.islink(bash_path) or os.path.isfile(bash_path):
            return bash_path
        real = shutil.which("bash") or ""
        if real and os.path.isfile(real):
            return real
        for candidate in ("/bin/sh", "/system/bin/sh", shutil.which("sh") or ""):
            if candidate and os.path.isfile(candidate):
                try:
                    os.symlink(candidate, bash_path)
                    self.output.info(f"HMBS bash shim: {bash_path} -> {candidate}")
                    return bash_path
                except OSError as exc:
                    self.output.warning(f"HMBS bash shim failed: {exc}")
                    return ""
        return ""

    def _sign_build_artifacts(self):
        # Upstream keeps test binaries in tests/ (utest_*) and in
        # tests/fuzz/<name>/ (regress_fuzz_* harnesses + fuzz_regression_test),
        # with libyang.so in the CMake binary-dir root; sign the whole build
        # tree's ELFs recursively (the helper filters non-ELF files itself).
        # The previous top-level glob (tests/*) missed the fuzz harnesses,
        # which fork+exec on device and would fail unsigned.
        candidates = glob.glob(
            os.path.join(self.build_folder, "**", "*.so*"), recursive=True
        )
        candidates.extend(
            glob.glob(os.path.join(self.build_folder, "tests", "*"))
        )
        # Recursive sweep: fuzz harnesses, perf binary, plugins, tools.
        for dirpath, _, filenames in os.walk(self.build_folder):
            # Skip the writable tmp dirs (no ELFs there, avoids noise).
            if "hmbs-tmp" in dirpath or "test-tmp" in dirpath:
                continue
            for name in filenames:
                if name.endswith(".signing"):
                    continue
                candidates.append(os.path.join(dirpath, name))
        for tool in ("yanglint", "yangre"):
            candidates.append(os.path.join(self.build_folder, tool))
        # Also cover the resolved ctest binary dir when it differs from the
        # base build folder (cmake_layout per-config subdir).
        try:
            ctest_dir = self._ctest_dir()
        except Exception:
            ctest_dir = ""
        if ctest_dir and ctest_dir != self.build_folder:
            for dirpath, _, filenames in os.walk(ctest_dir):
                for name in filenames:
                    if name.endswith(".signing"):
                        continue
                    candidates.append(os.path.join(dirpath, name))
        self._sign_paths(candidates, required=True)

    def _sign_paths(self, paths, required):
        paths = sorted(
            {
                path
                for path in paths
                if os.path.isfile(path)
                and not os.path.islink(path)
                and self._is_elf(path)
            }
        )
        if not paths:
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            message = "HarmonyOS execution requires llvm-objcopy and binary-sign-tool"
            if required:
                raise ConanInvalidConfiguration(message)
            self.output.warning(message)
            return
        for path in paths:
            self._sign_elf_atomically(path, objcopy, signer)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(
                self._shell_join(
                    [objcopy, "--remove-section", ".codesign", temporary]
                ),
                env="conanbuild",
            )
            self.run(
                self._shell_join(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        temporary,
                        "-outFile",
                        temporary,
                        "-selfSign",
                        "1",
                    ]
                ),
                env="conanbuild",
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c", "") or compilers.get("cpp", "")
        compiler_dir = os.path.dirname(compiler)
        candidates = (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates if os.path.isfile(path)), "")

    def _shell_join(self, arguments):
        return shlex.join([str(argument) for argument in arguments])
