#!/usr/bin/env python3
"""Conan recipe - boost1.84-type_erasure 1.84.0 (Boost.TypeErasure split package).

Boost 1.84.0 component split package: delivers Boost.TypeErasure
(libboost_type_erasure.a + full boost header tree). Base: archives/b/boost/1.84.0
meta package (manual-compile approach) and boost1.84-coroutine/iostreams
split packages (standalone-package pattern).

Upstream: https://github.com/boostorg/type_erasure (tag boost-1.84.0).
Super-project source: boost_1_84_0.tar.gz (same as boost/1.84.0 meta package).

Library sources (libs/type_erasure/build authority: single translation unit):
  libs/type_erasure/src/dynamic_binding.cpp
(dynamic binding registry; upstream build/Jamfile.v2 links it against
/boost//thread for boost::shared_mutex, but no thread split package exists
on OHOS, so build() rewrites the process-local registry mutex to C++17
std::shared_mutex with identical shared/exclusive semantics; -pthread is
kept for the std RW mutex, no libboost_thread link needed).

Boost b2 build system is incompatible with OHOS (E068, see meta-package
notes.md), so the single TU is compiled manually with the Conan-provided
OHOS clang driver and archived with llvm-ar.

Upstream tests (libs/type_erasure/test, test/Jamfile.jam authority):
  run 31 + compile 5 + compile-fail 24 = 60 targets.
b2 is bypassed on OHOS: run tests are compiled with the header-only
boost.test single-header variant (included/unit_test.hpp, same trick as the
boost1.84-coroutine package, no libboost_unit_test_framework link needed);
compile-only tests use -fsyntax-only (expect success); compile-fail tests
use -fsyntax-only (expect failure, negative tests).
"""
import glob
import json
import os
import shutil
import signal
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostTypeErasureConan(ConanFile):
    name = "boost1.84-type_erasure"
    version = "1.84.0"
    description = "Boost.TypeErasure 1.84.0 split component package (runtime polymorphism without inheritance, libboost_type_erasure static library, HarmonyOS PC port)"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/doc/libs/1_84_0/doc/html/boost_typeerasure.html"
    url = "https://github.com/boostorg/type_erasure"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    # Boost source tree has 50k+ files; copying it to the build folder on
    # OHOS HMDFS is extremely slow. The recipe only reads sources (patches
    # are applied via the conan patch mechanism), so compile directly in
    # source_folder (conan no_copy_source semantics, same as atomic/log/wave
    # and iostreams component packages).
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def _select_tool(self, conf_key, env_vars, commands, hard_fallbacks):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        candidates = []
        v = compilers.get(conf_key)
        if v:
            candidates.append(v)
        for e in env_vars:
            ev = os.environ.get(e)
            if ev:
                candidates.append(ev.split()[0])
        for c in commands:
            w = shutil.which(c)
            if w:
                candidates.append(w)
            candidates.append(c)
        candidates.extend(hard_fallbacks)
        for cand in candidates:
            if not cand:
                continue
            cand = cand.strip().strip('"').strip("'")
            if not cand:
                continue
            if os.path.isabs(cand):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
                continue
            w = shutil.which(cand)
            if w and os.path.isfile(w) and os.access(w, os.X_OK):
                return w
        # Last resort: return the configured value (or plain command) so the
        # failure message still shows what was attempted.
        return compilers.get(conf_key) or commands[0]

    def _cxx(self):
        return self._select_tool(
            "cpp", ("CXX", "CC"),
            ("clang++",),
            ("/data/service/hnp/bin/clang++",
             "/storage/Users/currentUser/usr/local/bin/clang++"))

    def _ar(self):
        return self._select_tool(
            "ar", ("AR",),
            ("llvm-ar", "ar"),
            ("/data/service/hnp/bin/llvm-ar",
             "/storage/Users/currentUser/usr/local/bin/llvm-ar"))

    def _writable_tmpdir(self):
        # HMBS E002: /tmp may be read-only erofs on HarmonyOS. Reuse the
        # injected HMBS_TMPDIR/TMPDIR/TMP/TEMP when present, else fall back
        # to a build_folder subdirectory (same approach as coroutine package).
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            v = os.environ.get(var)
            if v and v != "0" and v != "/tmp":
                try:
                    os.makedirs(v, exist_ok=True)
                except OSError:
                    pass
                return v
        v = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if v and v != "0" and v != "/tmp":
            try:
                os.makedirs(v, exist_ok=True)
            except OSError:
                pass
            if v:
                return v
        base = self.build_folder or self.source_folder or os.getcwd()
        cand = os.path.join(base, "tmp_hmbs")
        try:
            os.makedirs(cand, exist_ok=True)
        except OSError:
            return base
        return cand

    def _cxxflags(self, boost_root):
        # Optimization flags driven by build_type (R8: no hardcoded build profile).
        if self.settings.build_type == "Debug":
            opt_flags = ["-O0", "-g"]
        else:
            opt_flags = ["-O2", "-DNDEBUG"]
        return " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            "-pthread",
            *opt_flags,
            "-fPIC",
            f"-I{boost_root}",
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_SYSTEM_NO_DEPRECATED",
            "-DBOOST_TYPE_ERASURE_NO_LIB",
            "-DBOOST_TYPE_ERASURE_STATIC_LINK",
            # R8 compliance: skip pthread_setcancelstate (not available on
            # OHOS musl) via a feature-detection macro instead of a platform
            # macro (__OHOS__). The patch consumes
            # BOOST_SP_NO_PTHREAD_SETCANCELSTATE, see patches/0001.
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
        ])

    def _run_cmd(self, cmd, timeout, shell=False, env=None):
        """Run a command with a hard timeout, killing the whole process group
        on timeout so no orphaned child (e.g. clang++) keeps the CI worker busy.

        stdin is redirected to DEVNULL: if an upstream test tries to read from
        stdin it immediately gets EOF instead of hanging (interactive-test
        protection, per CI environment-issue guidance).

        HMBS readonly_tmp: /tmp is read-only erofs on HarmonyOS. The child
        environment always carries the writable TMPDIR/TMP/TEMP (from HMBS
        injection or build_folder/tmp_hmbs fallback) so clang/boost.test
        temp files never fall back to /tmp. Callers must use list-form cmd
        (shell=False) with this env to avoid /bin/sh heredoc temp files in
        /tmp (preflight.sh[306] can't create /tmp/sh*.tmp).
        """
        base = dict(os.environ)
        if env is not None:
            base.update(env)
        # Ensure writable tmp vars; never leave them as /tmp or empty.
        tmpdir = (base.get("TMPDIR") or base.get("HMBS_TMPDIR")
                  or os.environ.get("TMPDIR") or os.environ.get("HMBS_TMPDIR"))
        if not tmpdir or tmpdir in ("0", "/tmp"):
            try:
                tmpdir = self._writable_tmpdir()
            except Exception:
                tmpdir = None
        if tmpdir:
            for k in ("TMPDIR", "TMP", "TEMP"):
                if not base.get(k) or base.get(k) in ("0", "/tmp"):
                    base[k] = tmpdir
            if not base.get("HMBS_TMPDIR") or base.get("HMBS_TMPDIR") in ("0", "/tmp"):
                base["HMBS_TMPDIR"] = tmpdir
        proc = subprocess.Popen(
            cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, stdin=subprocess.DEVNULL, start_new_session=True, env=base)
        try:
            out, err = proc.communicate(timeout=timeout)
            return proc.returncode, out, err
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                proc.kill()
            out, err = proc.communicate()
            return -1, out, err

    def _find_libcxx_dir(self):
        """Locate the SDK libc++_shared.so directory via compiler introspection.

        Same approach as the boost/1.90.0.2.1 test_package: ask clang where
        libc++_shared.so lives instead of hardcoding an SDK version path.
        """
        cxx = self._cxx()
        try:
            out = subprocess.check_output(
                [cxx, "-print-file-name=libc++_shared.so"], text=True).strip()
        except Exception as exc:  # noqa: BLE001 - introspection failure is reported below
            self.output.warning(f"libc++_shared.so introspection failed: {exc}")
            return None
        if not out or out == "libc++_shared.so":
            return None
        return os.path.dirname(out)

    # Upstream test inventory (libs/type_erasure/test/Jamfile.jam @ boost-1.84.0).
    # run 31: all linked against /boost//unit_test_framework upstream; on OHOS
    # they are built with the header-only included/unit_test.hpp variant
    # (same trick as boost1.84-coroutine), so no UTF library is compiled.
    # Only test_dynamic_any_cast additionally links /boost//type_erasure.
    _RUN_TESTS = [
        "test_binding.cpp",
        "test_increment.cpp",
        "test_add.cpp",
        "test_add_assign.cpp",
        "test_callable.cpp",
        "test_reference.cpp",
        "test_construct.cpp",
        "test_relaxed.cpp",
        "test_assign.cpp",
        "test_construct_ref.cpp",
        "test_construct_cref.cpp",
        "test_any_cast.cpp",
        "test_binding_of.cpp",
        "test_typeid_of.cpp",
        "test_nested.cpp",
        "test_less.cpp",
        "test_equal.cpp",
        "test_negate.cpp",
        "test_dereference.cpp",
        "test_subscript.cpp",
        "test_forward_iterator.cpp",
        "test_tuple.cpp",
        "test_stream.cpp",
        "test_deduced.cpp",
        "test_same_type.cpp",
        "test_member.cpp",
        "test_null.cpp",
        "test_free.cpp",
        "test_is_empty.cpp",
        "test_dynamic_any_cast.cpp",
        "test_limits.cpp",
    ]
    # compile 5: compile-only (expect success).
    _COMPILE_TESTS = [
        "test_param.cpp",
        "test_is_subconcept.cpp",
        "test_sfinae.cpp",
        "test_interface_order.cpp",
        "test_is_placeholder.cpp",
    ]
    # compile-fail 24: must fail to compile (negative tests, expect failure).
    _COMPILE_FAIL_TESTS = [
        "fail_default_construct.cpp",
        "fail_construct_mismatch.cpp",
        "fail_construct_mismatch_ref.cpp",
        "fail_construct_mismatch_cref.cpp",
        "fail_construct_mismatch_rref.cpp",
        "fail_binding_convert_no_mapping.cpp",
        "fail_increment_discard_const.cpp",
        "fail_not_incrementable.cpp",
        "fail_ref_assign.cpp",
        "fail_cref_assign.cpp",
        "fail_rref_assign.cpp",
        "fail_ref_discard_const.cpp",
        "fail_ref_discard_const_convert.cpp",
        "fail_ref_discard_const_convert_ref.cpp",
        "fail_ref_discard_const_convert_cref.cpp",
        "fail_ref_discard_const_init.cpp",
        "fail_any_cast_discard_const1.cpp",
        "fail_any_cast_discard_const2.cpp",
        "fail_any_cast_discard_const3.cpp",
        "fail_any_cast_discard_const4.cpp",
        "fail_any_cast_discard_const5.cpp",
        "fail_any_cast_discard_const6.cpp",
        "fail_any_cast_pointer_to_ref.cpp",
        "fail_any_cast_pointer_to_val.cpp",
    ]

    def build(self):
        apply_conandata_patches(self)
        self._patch_type_erasure_std_mutex()
        tmpdir = self._writable_tmpdir()
        for k in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            os.environ[k] = tmpdir
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        self.output.info(f"[HMBS tmp] using writable TMPDIR={tmpdir}")

        boost_root = self.source_folder
        cxx = self._cxx()
        ar = self._ar()
        cxxflags = self._cxxflags(boost_root)

        # -- TypeErasure component (1 TU) ----------------------------------
        # NOTE: os.environ TMPDIR/TMP/TEMP already points to the writable
        # HMBS tmpdir above, so no TMPDIR= prefix (avoids extra /bin/sh
        # quoting/temp-file handling on readonly /tmp).
        obj_dir = os.path.join(self.build_folder, "obj_type_erasure")
        os.makedirs(obj_dir, exist_ok=True)
        src = os.path.join(boost_root, "libs", "type_erasure", "src",
                           "dynamic_binding.cpp")
        obj = os.path.join(obj_dir, "dynamic_binding.o")
        self.run(f'"{cxx}" {cxxflags} -c "{src}" -o "{obj}"')
        lib_path = os.path.join(self.build_folder, "libboost_type_erasure.a")
        self.run(f'"{ar}" rcs "{lib_path}" "{obj}"')

        # -- Upstream tests (b2 incompatible E068, driven manually) --------
        self._run_upstream_tests(boost_root, cxxflags)

    def _patch_type_erasure_std_mutex(self):
        """OHOS portability: use std::shared_mutex in dynamic_binding.cpp.

        Upstream build/Jamfile.v2 declares
        `lib boost_type_erasure : dynamic_binding.cpp /boost//thread ;`,
        i.e. the registry mutex comes from the compiled Boost.Thread
        library. No boost1.84-thread split package exists on OHOS, so the
        process-local static registry uses the C++17 standard equivalent
        (same shared lookup / exclusive register semantics, no compiled
        thread lib needed; -pthread is kept for the std RW mutex).

        Done as an idempotent in-place string rewrite instead of a unified
        diff patch: the conan patch parser rejected the hand-written hunk
        headers twice (Failed to parse patch), while exact-token replacement
        is immune to hunk counts, CRLF and context drift. Re-running on an
        already patched tree is a no-op followed by verification.
        """
        path = os.path.join(self.source_folder, "libs", "type_erasure",
                            "src", "dynamic_binding.cpp")
        with open(path, "r", encoding="utf-8", errors="ignore",
                   newline="") as fh:
            content = fh.read()
        orig = content
        content = content.replace(
            "#include <boost/thread/shared_mutex.hpp>",
            "#include <shared_mutex>")
        content = content.replace(
            "#include <boost/thread/lock_types.hpp>",
            "// OHOS: boost thread lock header removed"
            " (std lock types used instead)")
        content = content.replace(
            "typedef ::boost::shared_mutex mutex_type;",
            "typedef ::std::shared_mutex mutex_type;")
        content = content.replace(
            "::boost::unique_lock<mutex_type>",
            "::std::unique_lock<mutex_type>")
        content = content.replace(
            "::boost::shared_lock<mutex_type>",
            "::std::shared_lock<mutex_type>")
        if content != orig:
            with open(path, "w", encoding="utf-8", newline="") as out:
                out.write(content)
            self.output.info(
                "[OHOS] dynamic_binding.cpp registry mutex switched to"
                " std::shared_mutex")
        for marker in ("#include <shared_mutex>",
                       "typedef ::std::shared_mutex mutex_type;",
                       "::std::unique_lock<mutex_type>",
                       "::std::shared_lock<mutex_type>"):
            if marker not in content:
                raise Exception(
                    "std::shared_mutex port failed, missing "
                    f"{marker} in dynamic_binding.cpp")
        for leftover in ("#include <boost/thread/shared_mutex.hpp>",
                         "#include <boost/thread/lock_types.hpp>",
                         "::boost::shared_mutex",
                         "::boost::unique_lock<mutex_type>",
                         "::boost::shared_lock<mutex_type>"):
            if leftover in content:
                raise Exception(
                    "std::shared_mutex port incomplete, leftover "
                    f"{leftover} in dynamic_binding.cpp")

    def _patch_unit_test_include(self, src, dst, tmpdir=None):
        """Rewrite boost.test header include to the single-header variant.

        Upstream tests include <boost/test/unit_test.hpp> (needs the compiled
        UTF library). The header-only <boost/test/included/unit_test.hpp>
        ships the same test framework without linking (same trick as the
        boost1.84-coroutine package). Returns True when the file was patched.

        HMBS readonly_tmp: if the test source hardcodes /tmp (read-only erofs
        on HarmonyOS), only the temp-file root is replaced with the writable
        tmpdir; no test is skipped or deleted.
        """
        with open(src, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()
        orig = content
        patched = content.replace(
            "#include <boost/test/unit_test.hpp>",
            "#include <boost/test/included/unit_test.hpp>")
        if tmpdir and tmpdir not in ("0", "/tmp") and "/tmp" in patched:
            patched = patched.replace("/tmp", tmpdir)
        with open(dst, "w", encoding="utf-8") as out:
            out.write(patched)
        if patched != orig and "/tmp" in orig and tmpdir:
            self.output.info(f"[HMBS tmp] replaced hardcoded /tmp with {tmpdir} in {os.path.basename(dst)}")
        return patched != orig

    def _run_upstream_tests(self, boost_root, cxxflags):
        """Compile and run Boost.TypeErasure upstream tests (bypassing b2).

        run 31: compile with the header-only boost.test variant and execute
          (exit code 0 = pass). Only test_dynamic_any_cast links
          -lboost_type_erasure; the rest are header-only.
        compile 5: -fsyntax-only, success expected.
        compile-fail 24: -fsyntax-only, failure expected (negative tests).
        Report written to build_folder/upstream-tests-report.txt and the
        HMBS_UPSTREAM_TEST_RESULT machine-evidence line is emitted.
        """
        cxx = self._cxx()
        lib_dir = self.build_folder
        test_dir = os.path.join(boost_root, "libs", "type_erasure", "test")
        patch_dir = os.path.join(self.build_folder, "upstream_test_patched")
        os.makedirs(patch_dir, exist_ok=True)
        # Writable tmp root for this run (HMBS injection preferred).
        tmpdir = os.environ.get("TMPDIR") or os.environ.get("HMBS_TMPDIR")
        if not tmpdir or tmpdir in ("0", "/tmp"):
            tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        self.output.info(f"[HMBS tmp] upstream tests using TMPDIR={tmpdir}")

        # OHOS: upstream test binaries dynamically depend on the SDK
        # libc++_shared.so; locate it via compiler introspection and inject
        # LD_LIBRARY_PATH at run time (no hardcoded SDK version path).
        libcxx_dir = self._find_libcxx_dir() if self.settings.os == "OHOS" else None
        base_env = {"TMPDIR": tmpdir, "TMP": tmpdir, "TEMP": tmpdir,
                    "HMBS_TMPDIR": tmpdir}
        if libcxx_dir:
            base_env["LD_LIBRARY_PATH"] = (
                f"{libcxx_dir}:{os.environ.get('LD_LIBRARY_PATH', '')}"
            )

        report_lines = []
        passed, failed = 0, 0

        def record(ok, line):
            nonlocal passed, failed
            report_lines.append(f"{'PASS' if ok else 'FAIL'} {line}")
            if ok:
                passed += 1
            else:
                failed += 1

        def _split_flags(flag_str):
            # cxxflags is a simple space-separated string without quoted
            # spaces (paths with spaces are passed as separate list items
            # below), so a plain split is sufficient and avoids /bin/sh.
            return flag_str.split()

        test_flags = f"{cxxflags} -DBOOST_TEST_NO_LIB"
        flag_list = _split_flags(test_flags)
        for src_name in self._RUN_TESTS:
            src = os.path.join(test_dir, src_name)
            if not os.path.isfile(src):
                record(False, f"{src_name} SOURCE_MISSING")
                continue
            patched = os.path.join(patch_dir, src_name)
            self._patch_unit_test_include(src, patched, tmpdir)
            exe = os.path.join(lib_dir, "ut_" + src_name.replace(".cpp", ""))
            cmd = [cxx] + flag_list + [patched, "-o", exe]
            if src_name == "test_dynamic_any_cast.cpp":
                cmd += [f"-L{lib_dir}", "-lboost_type_erasure"]
            ret_code, _, ret_err = self._run_cmd(cmd, timeout=600, shell=False, env=base_env)
            if ret_code != 0:
                snippet = ret_err.strip().replace("\n", " ")[:2000] if ret_err.strip() else ""
                record(False, f"{src_name} COMPILE_FAIL rc={ret_code}: {snippet}")
                continue
            run_code, run_out, run_err = self._run_cmd([exe], timeout=300, env=base_env)
            ok = run_code == 0
            detail = (run_out or run_err or "").strip().splitlines()
            last = detail[-1][:500] if detail else ""
            if not ok:
                full = (run_out or run_err or "").strip().replace("\n", " ")[:2000]
                record(ok, f"{src_name} rc={run_code} ({last}) FULL:{full}")
            else:
                record(ok, f"{src_name} rc={run_code}"
                       f"{f' ({last})' if detail else ''}")

        for src_name in self._COMPILE_TESTS:
            src = os.path.join(test_dir, src_name)
            if not os.path.isfile(src):
                record(False, f"{src_name} SOURCE_MISSING")
                continue
            patched = os.path.join(patch_dir, src_name)
            self._patch_unit_test_include(src, patched, tmpdir)
            cmd = [cxx] + flag_list + ["-fsyntax-only", patched]
            ret_code, _, ret_err = self._run_cmd(cmd, timeout=300, shell=False, env=base_env)
            if ret_code == 0:
                record(True, f"{src_name} (compile expectation, rc=0)")
            else:
                snippet = ret_err.strip().replace("\n", " ")[:2000] if ret_err.strip() else ""
                record(False, f"{src_name} (compile expectation, rc={ret_code}): {snippet}")

        for src_name in self._COMPILE_FAIL_TESTS:
            src = os.path.join(test_dir, src_name)
            if not os.path.isfile(src):
                record(False, f"{src_name} SOURCE_MISSING")
                continue
            # Negative tests: also route any hardcoded /tmp through a
            # patched copy (same minimal root-replacement, expectation
            # unchanged: compilation must fail).
            patched_cf = os.path.join(patch_dir, src_name)
            try:
                with open(src, "r", encoding="utf-8", errors="ignore") as fh:
                    cf_content = fh.read()
                if tmpdir and "/tmp" in cf_content:
                    cf_content = cf_content.replace("/tmp", tmpdir)
                    with open(patched_cf, "w", encoding="utf-8") as out:
                        out.write(cf_content)
                    self.output.info(f"[HMBS tmp] replaced hardcoded /tmp with {tmpdir} in {src_name}")
                    src = patched_cf
            except OSError as e:
                self.output.warning(f"tmp patch copy failed for {src_name}: {e}")
            cmd = [cxx] + flag_list + ["-fsyntax-only", src]
            ret_code, _, _ = self._run_cmd(cmd, timeout=300, shell=False, env=base_env)
            record(ret_code != 0,
                   f"{src_name} (compile-fail expectation, rc={ret_code})")

        total = passed + failed
        report_lines.append(f"TOTAL {total}: {passed} passed / {failed} failed")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(f"upstream test report: {report_path} ({passed}/{total} passed)")
        # Always emit every FAIL line (not just the tail) so the preflight
        # log identifies the failing target even when it is not in the last 8.
        for line in report_lines:
            if line.startswith("FAIL"):
                self.output.info(f"[upstream-tests] {line}")
        for line in report_lines[-8:]:
            if line.startswith(("PASS", "TOTAL")):
                self.output.info(f"[upstream-tests] {line}")
        if failed:
            raise Exception(f"Upstream tests failed: {failed}/{total} - see {report_path}")

        discovered = (len(self._RUN_TESTS) + len(self._COMPILE_TESTS)
                      + len(self._COMPILE_FAIL_TESTS))
        ut_result = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "boost.test",
            "command": ("clang++ libs/type_erasure/test/test_*.cpp "
                        "(included/unit_test.hpp) && ./ut_*; "
                        "clang++ -fsyntax-only test_param/is_subconcept/sfinae/..."
                        "; clang++ -fsyntax-only fail_* (expect failure)"),
            "discovered": discovered,
            "executed": total,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        json_path = os.path.join(self.build_folder, "upstream_test_result.json")
        try:
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(ut_result, jf)
            self.output.info(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")
            print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")
        except OSError as e:
            self.output.warning(f"failed to write upstream_test_result.json: {e}")

    def package(self):
        # Full Boost header tree (patched): the component package is
        # self-contained (same pattern as the iostreams split package),
        # downstream consumers do not need the boost/1.84.0 meta package.
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE_1_0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # Install the compiled static library.
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_type_erasure.a")):
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

        # Persist upstream test evidence for test_package re-emission.
        resdir = os.path.join(self.package_folder, "res")
        for fname in ("upstream_test_result.json", "upstream-tests-report.txt"):
            src = os.path.join(self.build_folder, fname)
            if os.path.isfile(src):
                copy(self, fname, src=self.build_folder, dst=resdir)

    def package_info(self):
        # The split component package uses its own CMake package name
        # boost1.84-type_erasure to avoid CMakeDeps file clashes with the
        # boost/1.84.0 meta package's cmake_file_name "Boost" (same as the
        # atomic/log/wave/iostreams precedents).
        self.cpp_info.set_property("cmake_file_name", "boost1.84-type_erasure")

        # Main "headers" component (always needed).
        self.cpp_info.components["boost1.84_type_erasure_headers"].includedirs = ["include"]
        # R8 compliance: expose BOOST_SP_NO_PTHREAD_SETCANCELSTATE to all
        # consumers so the patched sp_thread_sleep.hpp skips the
        # pthread_setcancelstate path (not available on OHOS musl).
        self.cpp_info.components["boost1.84_type_erasure_headers"].defines = [
            "BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        self.cpp_info.components["boost1.84_type_erasure_headers"].set_property(
            "cmake_target_name", "boost1.84-type_erasure::headers")

        # type_erasure (the component this package delivers).
        self.cpp_info.components["boost1.84_type_erasure"].includedirs = []
        self.cpp_info.components["boost1.84_type_erasure"].libs = ["boost_type_erasure"]
        # std::shared_mutex registry TU is compiled with -pthread.
        self.cpp_info.components["boost1.84_type_erasure"].system_libs = ["pthread"]
        self.cpp_info.components["boost1.84_type_erasure"].requires = [
            "boost1.84_type_erasure_headers"]
        self.cpp_info.components["boost1.84_type_erasure"].set_property(
            "cmake_target_name", "boost1.84-type_erasure::type_erasure")
