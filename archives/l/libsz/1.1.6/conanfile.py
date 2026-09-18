#!/usr/bin/env python3
"""Conan recipe — libsz 1.1.6 (CMake).

libsz is the SZIP-compatible compression library shipped inside the
upstream libaec source tree (Adaptive Entropy Coding for integer data).
The same source tree also builds libaec; this recipe builds and packages
both libraries from the single upstream release.

Upstream tests: 7 CTest cases registered by tests/CMakeLists.txt
(check_code_options, check_buffer_sizes, check_seeking, check_long_fs,
check_szcomp, check_rsi_block_access, sampledata.sh). All fixtures live
in the release tarball (data/121B2TestData), no network needed. build()
runs the full suite via `ctest --output-on-failure`, counts the real
framework verdicts, emits HMBS_UPSTREAM_TEST_RESULT, and fails closed on
any deviation (non-zero exit, missing summary, silent skip).
"""

import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibszConan(ConanFile):
    name = "libsz"
    version = "1.1.6"
    description = "SZIP-compatible compression library from the libaec source tree"
    license = "BSD-2-Clause"
    homepage = "https://github.com/Deutsches-Klimarechenzentrum/libaec"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libsz supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # E002/readonly_tmp: export the writable tmpdir via buildenv
        # (conanbuild.sh) so EVERY cmake/clang child inherits it.
        # os.environ in build() alone is not enough: conan buildenv
        # isolation resets the env cmake children see (libfduserdata
        # precedent), leaving clang temp files on read-only /tmp.
        tmp = self._effective_tmpdir()
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmp
            try:
                self.buildenv_info.define(var, tmp)
            except Exception:
                pass
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = (
            "ON" if self.options.shared else "OFF"
        )
        tc.variables["BUILD_STATIC_LIBS"] = (
            "OFF" if self.options.shared else "ON"
        )
        tc.variables["BUILD_TESTING"] = True
        if self.settings.os == "OHOS":
            # Strategy-cycle 2 (new route): previous 3 rounds chased
            # TMPDIR/buildenv/try-compile-link/LD_LIBRARY_PATH and the
            # project() failure did not move, so the root cause is not
            # the link step. The log's first visible symptom is
            # "System is unknown to cmake, create: Platform/HarmonyOS"
            # from CMakeToolchain mapping os=OHOS to
            # CMAKE_SYSTEM_NAME=HarmonyOS, which vanilla CMake 4.4.3 on
            # the device does not recognise; the compiler id/ABI
            # detection in project() then collapses with
            # "The CMAKE_C_COMPILER: /data/service/hnp/bin/clang ...
            # Configuring incomplete". Follow the repo-verified zxc
            # 0.9.1 / function2 4.2.3 route instead: native build maps
            # the system to Linux/aarch64 (worker IS aarch64, binaries
            # still run natively) and pins the minimum policy for
            # CMake 4.x. The STATIC_LIBRARY try-compile bypass is
            # dropped: it only masked the real detection failure and
            # never changed the error across 3 rounds.
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def _effective_tmpdir(self):
        # HMBS readonly_tmp: /tmp is read-only on the device. Reuse the
        # HMBS-injected writable temp root when it exists and is really
        # writable (probe with makedirs + write + unlink); otherwise fall
        # back to a build_folder subdir (always writable in build()).
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key, "")
            if val:
                try:
                    os.makedirs(val, exist_ok=True)
                    probe = os.path.join(val, ".tmp-write-probe")
                    with open(probe, "w") as _pf:
                        _pf.write("ok")
                    os.unlink(probe)
                    return val
                except OSError:
                    continue
        fallback = os.path.join(self.build_folder, "hmbs-tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _subprocess_env(self):
        tmp = self._effective_tmpdir()
        env = dict(os.environ)
        env["TMPDIR"] = tmp
        env["TMP"] = tmp
        env["TEMP"] = tmp
        # Some toolchains/scripts consult TEST_TMPDIR instead of TMPDIR.
        env["TEST_TMPDIR"] = tmp
        fallback = env.get("HMBS_AUTOCONF_MKTEMP_FALLBACK") or os.path.join(
            tmp, "mktemp-fallback")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        env["HMBS_AUTOCONF_MKTEMP_FALLBACK"] = fallback
        sdk_lib = self._sdk_llvm_libdir()
        if sdk_lib:
            prev = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                p for p in (sdk_lib, prev) if p)
        return env

    def _ctest_dir(self):
        # cmake_layout builds out-of-source (build/Release); running ctest
        # at self.build_folder root finds zero tests. Locate the real dir
        # holding CTestTestfile.cmake instead.
        for cand_dir in (
            os.path.join(self.build_folder, "build", "Release"),
            os.path.join(self.build_folder, "build"),
        ):
            if os.path.isfile(os.path.join(cand_dir, "CTestTestfile.cmake")):
                return cand_dir
        hits = glob.glob(os.path.join(
            self.build_folder, "**", "CTestTestfile.cmake"), recursive=True)
        if hits:
            return os.path.dirname(hits[0])
        return self.build_folder

    def _find_ctest(self):
        # Prefer the ctest next to HMBS_CMAKE (same toolchain as CI);
        # plain `ctest` from PATH is only a fallback.
        hmbs_cmake = os.environ.get("HMBS_CMAKE", "")
        cand = os.path.join(os.path.dirname(hmbs_cmake), "ctest")
        if hmbs_cmake and os.path.isfile(cand):
            return cand
        exe = shutil.which("ctest")
        if exe:
            return exe
        return "ctest"

    def _conf_cc(self):
        # Raw conf value (no probing here; probing happens in build
        # under the scoped env via _verified_compilers).
        try:
            comp = self.conf.get(
                "tools.build:compiler_executables", default={},
                check_type=dict) or {}
        except Exception:
            comp = {}
        cc = comp.get("c", "")
        if cc and os.path.isfile(cc):
            return cc
        if cc:
            found = shutil.which(os.path.basename(cc))
            if found:
                return found
        return shutil.which("clang") or cc or "clang"

    def _verified_compilers(self, run_env):
        # Experience 1 (libaiff): do not trust isfile/X_OK (R49: X_OK
        # is恒False on HMDFS). Verify usability by actually running
        # `<cand> --version` under the scoped build env; prefer the
        # PATH-resolved executable, conf absolute path only as fallback.
        try:
            comp = self.conf.get(
                "tools.build:compiler_executables", default={},
                check_type=dict) or {}
        except Exception:
            comp = {}
        conf_c = comp.get("c", "") or ""
        conf_cpp = comp.get("cpp", "") or comp.get("cxx", "") or ""
        c_cands = []
        for cand in (shutil.which("clang"), conf_c,
                     (shutil.which(os.path.basename(conf_c))
                      if conf_c else ""), os.environ.get("CC", ""),
                     "clang"):
            if cand and cand not in c_cands:
                c_cands.append(cand)
        cxx_cands = []
        for cand in (shutil.which("clang++"), conf_cpp,
                     (shutil.which(os.path.basename(conf_cpp))
                      if conf_cpp else ""), os.environ.get("CXX", ""),
                     "clang++"):
            if cand and cand not in cxx_cands:
                cxx_cands.append(cand)

        def _runs(cand):
            try:
                proc = subprocess.run(
                    [cand, "--version"], stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True, timeout=60,
                    env=run_env)
                out = (proc.stdout or "")[:400]
                if proc.returncode == 0 and (
                        "clang" in out.lower()
                        or "version" in out.lower()):
                    return True
                self.output.info(
                    "compiler candidate rejected %r rc=%s out=%.120s"
                    % (cand, proc.returncode, out))
            except Exception as exc:
                self.output.info(
                    "compiler candidate unrunnable %r: %r" % (cand, exc))
            return False

        cc = next((c for c in c_cands if c and _runs(c)), "")
        cxx = next((c for c in cxx_cands if c and _runs(c)), "")
        if not cc:
            cc = conf_c or "clang"
        if not cxx:
            cxx = conf_cpp or "clang++"
        self.output.info("verified compilers: CC=%s CXX=%s" % (cc, cxx))
        return cc, cxx

    def _rewrite_toolchain_compiler(self, cc, cxx):
        # Experience 1 (libaiff): CMake reads the compiler from the
        # generated conan_toolchain.cmake, not from our probe. If that
        # file pins a non-executable absolute path, project() reports
        # "compiler identification is unknown" even though a direct
        # `cc src -o out` probe passes. Rewrite the pinned paths to
        # the verified executables (generate() itself stays bare).
        tc_file = os.path.join(
            self.build_folder, "build", "Release", "generators",
            "conan_toolchain.cmake")
        if not os.path.isfile(tc_file):
            hits = glob.glob(os.path.join(
                self.build_folder, "**", "conan_toolchain.cmake"),
                recursive=True)
            tc_file = hits[0] if hits else ""
        if not tc_file or not os.path.isfile(tc_file):
            self.output.info("toolchain file not found, skip rewrite")
            return
        try:
            with open(tc_file, "r", encoding="utf-8") as fh:
                content = fh.read()
        except Exception as exc:
            self.output.warning("cannot read %s: %r" % (tc_file, exc))
            return
        orig = content
        for var, val in (("CMAKE_C_COMPILER", cc),
                         ("CMAKE_CXX_COMPILER", cxx)):
            if not val:
                continue
            content, n = re.subn(
                r'set\(\s*' + var + r'\b[^)]*\)',
                'set(%s "%s")' % (var, val), content, count=1)
            if n == 0:
                content += '\nset(%s "%s")\n' % (var, val)
        if content != orig:
            try:
                with open(tc_file, "w", encoding="utf-8",
                           newline="\n") as fh:
                    fh.write(content)
                self.output.info(
                    "rewrote toolchain compilers to CC=%s CXX=%s in %s"
                    % (cc, cxx, tc_file))
            except Exception as exc:
                self.output.warning(
                    "cannot rewrite %s: %r" % (tc_file, exc))

    def _sdk_llvm_libdir(self):
        # OHOS SDK lld is a host ELF needing libxml2.so.16; the loader
        # does not expand its $ORIGIN RUNPATH on some workers, so the
        # try_compile link step fails ("...not able to compile a simple
        # test program"). Derive llvm/lib from the ACTUAL compiler and
        # verify libxml2.so.16 is there (abseil/libvidstab pattern).
        # Returns "" when already covered / not OHOS (non-fatal).
        if str(self.settings.os) != "OHOS":
            return ""
        cc = self._conf_cc()
        candidates = []
        try:
            resource_dir = subprocess.check_output(
                [cc, "-print-resource-dir"],
                stderr=subprocess.DEVNULL, text=True,
                timeout=60).strip()
            if resource_dir:
                candidates.append(
                    os.path.dirname(os.path.dirname(resource_dir)))
        except Exception:
            pass
        try:
            real_cc = os.path.realpath(cc)
            candidates.append(os.path.join(
                os.path.dirname(os.path.dirname(real_cc)), "lib"))
        except Exception:
            pass
        for cand in dict.fromkeys(candidates):
            try:
                if os.path.isfile(os.path.join(cand, "libxml2.so.16")):
                    return cand
            except Exception:
                continue
        return ""

    def _build_environment(self):
        # Scoped env for cmake.configure/build: writable tmp root plus
        # the SDK linker runtime path (libvidstab precedent).
        env = Environment()
        tmp = self._effective_tmpdir()
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        sdk_lib = self._sdk_llvm_libdir()
        if sdk_lib:
            self.output.info(
                "OHOS SDK linker runtime path: %s" % sdk_lib)
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        return env

    def _probe_toolchain(self):
        # Fail fast with the REAL stderr: compile+link a minimal C
        # program with the profile compiler before cmake runs, so the
        # next log shows the true failure instead of a truncated
        # project() line (libogg smoke-test precedent).
        cc = self._conf_cc()
        probe_dir = os.path.join(self.build_folder, "hmbs-probe")
        os.makedirs(probe_dir, exist_ok=True)
        src = os.path.join(probe_dir, "cc_probe.c")
        out = os.path.join(probe_dir, "cc_probe")
        with open(src, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("int main(void){return 0;}\n")
        try:
            ver = subprocess.run(
                [cc, "--version"], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, timeout=60)
            first = (ver.stdout or "").strip().splitlines()
            self.output.info("probe compiler %s rc=%s %s" % (
                cc, ver.returncode,
                (first[0] if first else "")[:160]))
        except Exception as exc:
            raise ConanException(
                "libsz toolchain probe: cannot run %r: %r" % (cc, exc))
        proc = subprocess.run(
            [cc, src, "-o", out], stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, timeout=300)
        tail = (proc.stdout or "").strip().splitlines()[-15:]
        for line in tail:
            self.output.info("probe cc: %s" % line)
        if proc.returncode != 0 or not os.path.isfile(out):
            raise ConanException(
                "libsz toolchain probe: %s cannot compile+link "
                "(rc=%s): %s" % (cc, proc.returncode, " | ".join(tail)))
        self.output.info("probe compiler compile+link ok: %s" % cc)

    def build(self):
        apply_conandata_patches(self)
        tmp = self._effective_tmpdir()
        os.environ["TMPDIR"] = tmp
        os.environ["TMP"] = tmp
        os.environ["TEMP"] = tmp
        with self._build_environment().vars(self).apply():
            self._probe_toolchain()
            run_env = self._subprocess_env()
            cc, cxx = self._verified_compilers(run_env)
            self._rewrite_toolchain_compiler(cc, cxx)
            cmake = CMake(self)
            cmake.configure(variables={"CMAKE_C_COMPILER": cc,
                                       "CMAKE_CXX_COMPILER": cxx})
            cmake.build()
        self._run_upstream_tests()

    def _clean_ctest_result_files(self):
        # Remove stale CTest result files so any LastTest.log found after
        # the run is guaranteed to belong to the current invocation
        # (a stale pass log must never green a failed run).
        try:
            hits = glob.glob(os.path.join(
                self.build_folder, "**", "LastTest*.log"), recursive=True)
        except Exception:
            return
        for hit in hits:
            try:
                os.unlink(hit)
            except OSError:
                pass

    def _read_ctest_result_files(self, ctest_dir):
        """Fallback evidence: CTest's own machine-written result files.

        Returns (file_summary, file_passed, file_failed, file_secs,
        detail, file_content): the summary match in LastTest.log (or None),
        tests recorded Passed there, whether LastTestsFailed.log is
        non-empty, the Total Test time seconds (or None), a one-line detail
        string, and the normalised file content.
        """
        try:
            hits = glob.glob(os.path.join(
                self.build_folder, "**", "LastTest.log"), recursive=True)
        except Exception:
            hits = []
        log_file = ""
        for hit in hits or []:
            if hit.startswith(ctest_dir):
                log_file = hit
                break
        if not log_file and hits:
            log_file = hits[0]
        if not log_file:
            return None, [], False, None, "no LastTest.log under build tree", ""
        try:
            with open(log_file, "r", encoding="utf-8",
                       errors="replace") as fh:
                content = fh.read()
        except Exception as exc:
            return (None, [], False, None,
                    "cannot read %s: %r" % (log_file, exc), "")
        content = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", content)
        content = content.replace("\r", "")
        file_summary = re.search(
            r"(\d+)%\s+tests?\s+passed\s*(?:,\s*(\d+)\s+tests?\s+failed\s+)?"
            r"out\s+of\s+(\d+)",
            content,
        )
        file_passed = []
        for m in re.finditer(r"Test\s+#\d+:\s+(\S+)\b[\s.]*Passed", content):
            if m.group(1) not in file_passed:
                file_passed.append(m.group(1))
        file_failed = False
        failed_file = os.path.join(
            os.path.dirname(log_file), "LastTestsFailed.log")
        try:
            if os.path.isfile(failed_file):
                with open(failed_file, "r", encoding="utf-8",
                           errors="replace") as fh:
                    file_failed = bool(fh.read().strip())
        except Exception:
            file_failed = False
        file_secs = None
        m_time = re.search(r"Total Test time[^\d]*([\d.]+)\s*sec", content)
        if m_time:
            try:
                file_secs = float(m_time.group(1))
            except ValueError:
                file_secs = None
        detail = ("file=%s bytes=%d passed_in_file=%d failed_file=%s "
                  "total_time=%s" % (
                      log_file, len(content), len(file_passed),
                      ("NON-EMPTY" if file_failed else "empty/missing"),
                      (("%ss" % m_time.group(1)) if m_time else "missing")))
        return file_summary, file_passed, file_failed, file_secs, detail, content

    def _run_upstream_tests(self):
        """Run the full upstream CTest suite and emit the HMBS evidence.

        Fail-closed: any non-zero exit, missing summary line, discovered
        count of zero, or a test that did not report Passed turns the
        marker to failed and raises, so `conan create` cannot go green on
        an unruly or silently-skipped suite.
        """
        ctest = self._find_ctest()
        command = "ctest --output-on-failure"
        ctest_dir = self._ctest_dir()
        self.output.info("running upstream ctest in %s" % ctest_dir)
        run_env = self._subprocess_env()

        try:
            names_proc = subprocess.run(
                [ctest, "-N"],
                cwd=ctest_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=300,
                env=run_env,
            )
            names_output = names_proc.stdout.decode(
                "utf-8", errors="replace") if isinstance(
                    names_proc.stdout, (bytes, bytearray)) else (
                        names_proc.stdout or "")
        except Exception as exc:
            self._emit_upstream_marker(
                "failed", command, 0, 0, 0, 0, 0,
                f"ctest -N discovery failed: {exc!r}",
            )
            raise ConanException(f"libsz upstream test discovery failed: {exc!r}")

        discovered_names = re.findall(
            r"Test\s+#\d+:\s+(\S+)", names_output
        )
        discovered = len(discovered_names)
        if names_proc.returncode != 0 or discovered == 0:
            self._emit_upstream_marker(
                "failed", command, discovered, 0, 0, 0, 0,
                "ctest -N reported no tests; upstream suite is missing",
            )
            raise ConanException("libsz upstream suite discovered 0 tests")

        # Stale CTest logs must not green this run: drop them first so the
        # file fallback below only ever sees the current invocation.
        self._clean_ctest_result_files()
        try:
            proc = subprocess.run(
                [ctest, "--output-on-failure"],
                cwd=ctest_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=1200,
                env=run_env,
            )
            raw = proc.stdout.decode(
                "utf-8", errors="replace") if isinstance(
                    proc.stdout, (bytes, bytearray)) else (
                        proc.stdout or "")
            returncode = proc.returncode
        except Exception as exc:
            self._emit_upstream_marker(
                "failed", command, discovered, 0, 0, 0, 0,
                f"ctest harness could not run: {exc!r}",
            )
            raise ConanException(f"libsz upstream ctest failed to run: {exc!r}")

        # Normalise once: strip ANSI colour codes (ctest may emit them
        # even when piped on some workers) and CR characters so the
        # summary matcher is not defeated by terminal formatting or
        # line-ending quirks. The previous strict pattern
        # `(\d+)% tests passed, (\d+) tests? failed out of (\d+)` missed
        # genuine passes on the device (exit 0 + "Total Test time" present
        # but no match), failing the suite on a parse artifact instead of
        # a real test verdict.
        # Device-confirmed format (round-3 evidence): the worker's ctest
        # (.harmonybrew/bin/ctest) prints `100% tests passed out of 7`
        # with NO ", 0 tests failed" middle part, so the failed-count group
        # must be optional. Vanilla CMake keeps the long form; accept both.
        output = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", raw)
        output = output.replace("\r", "")
        summary = re.search(
            r"(\d+)%\s+tests?\s+passed\s*(?:,\s*(\d+)\s+tests?\s+failed\s+)?"
            r"out\s+of\s+(\d+)",
            output,
        )
        reason = ""
        passed = 0
        failed = 0
        executed = 0
        if returncode != 0:
            reason = f"ctest exited with code {returncode}"
        elif not summary:
            # Exit 0 but the stdout summary is missing (device observation
            # two rounds in a row: exit 0 + "Total Test time" present, yet
            # no summary match even with a whitespace/ANSI-tolerant
            # pattern). Different strategy from the stdout-only fix: use
            # CTest's own machine-written Testing/Temporary/LastTest.log
            # (+ LastTestsFailed.log), which no terminal formatting or
            # stdout filtering can alter. A pass is accepted only when
            # every discovered test has a real Passed verdict in the file,
            # the failed-test file is empty, and Total Test time is > 0
            # (so silent skips can never count as passes).
            (file_summary, file_passed, file_failed, file_secs,
             file_detail, file_content) = self._read_ctest_result_files(
                 ctest_dir)
            self.output.info("ctest file evidence: %s" % file_detail)
            for line in (file_content or "").splitlines():
                if ("tests passed" in line or "tests failed" in line
                        or "Total Test time" in line):
                    self.output.info(
                        "ctest file summary-line: %s" % line.strip()[:300])
            haystack = (output or "") + "\n" + (file_content or "")
            if file_summary is not None:
                percent = int(file_summary.group(1))
                failed = (int(file_summary.group(2))
                          if file_summary.group(2) is not None else 0)
                total = int(file_summary.group(3))
                passed = total - failed
                executed = total
                if total != discovered:
                    reason = ("ctest file total %d != discovered %d; %s"
                              % (total, discovered, file_detail))
                elif percent != 100 or failed != 0 or file_failed:
                    reason = ("ctest file summary reports %d failure(s) "
                              "out of %d; %s" % (failed, total, file_detail))
                else:
                    missing = [
                        test_name
                        for test_name in discovered_names
                        if not re.search(
                            r"Test\s+#\d+:\s+" + re.escape(test_name)
                            + r"\b[\s.]*Passed",
                            haystack,
                        )
                    ]
                    if missing:
                        reason = ("tests without a Passed verdict: "
                                  + ", ".join(missing))
                    else:
                        passed = discovered
                        executed = discovered
                        self.output.info(
                            "ctest file verdict: %d/%d Passed "
                            "(summary from LastTest.log, cross-checked "
                            "with stdout)" % (passed, discovered))
            elif (not file_failed and file_secs is not None
                    and file_secs > 0
                    and len(file_passed) >= discovered
                    and all(n in file_passed
                            for n in discovered_names)
                    and "Total Test time" in haystack):
                missing = [
                    test_name
                    for test_name in discovered_names
                    if not re.search(
                        r"Test\s+#\d+:\s+" + re.escape(test_name)
                        + r"\b[\s.]*Passed",
                        haystack,
                    )
                ]
                if missing:
                    reason = ("tests without a Passed verdict: "
                              + ", ".join(missing))
                else:
                    passed = discovered
                    executed = discovered
                    self.output.info(
                        "ctest file verdict: %d/%d Passed "
                        "(per-test verdicts from LastTest.log, "
                        "Total Test time %.2fs, failed file empty)"
                        % (passed, discovered, file_secs))
            else:
                reason = ("exit 0 but no ctest summary line in harness "
                          "output; " + file_detail)
        else:
            # Group 2 (failed count) is None for the short device form
            # `100% tests passed out of 7`; percent==100 then implies zero
            # failures, and the per-test Passed cross-check below rules out
            # silent skips either way.
            percent = int(summary.group(1))
            failed = (int(summary.group(2))
                      if summary.group(2) is not None else 0)
            total = int(summary.group(3))
            passed = total - failed
            executed = total
            if total != discovered:
                reason = (
                    f"ctest total {total} != discovered {discovered}"
                )
            elif percent != 100 or failed != 0:
                reason = (
                    f"ctest summary reports {failed} failure(s) "
                    f"out of {total}"
                )
            else:
                missing = [
                    test_name
                    for test_name in discovered_names
                    if not re.search(
                        r"Test\s+#\d+:\s+" + re.escape(test_name) + r"\b[\s.]*Passed",
                        output,
                    )
                ]
                if missing:
                    # The worker shim compacts stdout (876 bytes for the
                    # whole run); per-test lines may live only in CTest's
                    # result file. Cross-check there before failing so a
                    # real 7/7 pass is not rejected on a formatting detail.
                    # Strictness is unchanged: every test still needs a
                    # real Passed verdict from a framework source.
                    (_fsummary, _fpassed, _ffailed, _fsecs,
                     _fdetail, _fcontent) = self._read_ctest_result_files(
                         ctest_dir)
                    self.output.info(
                        "ctest file cross-check: %s" % _fdetail)
                    haystack = (output or "") + "\n" + (_fcontent or "")
                    missing = [
                        test_name
                        for test_name in discovered_names
                        if not re.search(
                            r"Test\s+#\d+:\s+" + re.escape(test_name) + r"\b[\s.]*Passed",
                            haystack,
                        )
                    ]
                if missing:
                    reason = (
                        "tests without a Passed verdict: "
                        + ", ".join(missing)
                    )
                else:
                    passed = discovered
                    executed = discovered

        if reason:
            self.output.info(
                "ctest harness debug: ctest=%s dir=%s rc=%s "
                "raw_bytes=%d discovered=%s names=%s" % (
                    ctest, ctest_dir, returncode, len(raw),
                    discovered, ",".join(discovered_names)))
            for line in output.splitlines():
                if ("tests passed" in line or "tests failed" in line
                        or "Total Test time" in line
                        or "No tests were found" in line):
                    self.output.info("ctest summary-line: %s" % line.strip())
            verdict_lines = [l.strip() for l in output.splitlines()
                             if re.search(r"Test\s+#\d+", l)]
            self.output.info(
                "ctest per-test verdicts (%d): %s" % (
                    len(verdict_lines), " | ".join(verdict_lines[-14:])))
            self.output.info(output[-20000:])
            self._emit_upstream_marker(
                "failed", command, discovered, executed, passed,
                failed, 0, reason,
            )
            raise ConanException(f"libsz upstream tests failed: {reason}")

        self._emit_upstream_marker(
            "passed", command, discovered, executed, passed, 0, 0, ""
        )

    def _emit_upstream_marker(self, status, command, discovered, executed,
                              passed, failed, skipped, reason):
        marker = {
            "status": status,
            "framework": "ctest",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if reason:
            marker["reason"] = reason
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        # Dual-channel emit (stdout + Conan output): HMBS preflight
        # scrapes raw stdout.
        print(msg, flush=True)
        self.output.info(msg)
        # Persist to build folder for package() -> res/ carry, so a later
        # cache-hit run (build() skipped) can still re-emit real evidence
        # from test_package.
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8") as _fh:
                json.dump(marker, _fh)
        except Exception:
            pass

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # Persist upstream evidence into the package for test_package
        # cache-hit re-emit (build() is skipped on cache hit, so test()
        # must re-print the persisted real result every run).
        try:
            _src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(_src):
                _dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(_dst_dir, exist_ok=True)
                shutil.copyfile(
                    _src, os.path.join(_dst_dir, "hmbs_upstream.json"))
                self.output.info("[hmbs] persisted hmbs_upstream.json to res/")
        except Exception as _e:
            self.output.warning("persist hmbs_upstream.json failed: %r" % (_e,))

    def package_info(self):
        self.cpp_info.libs = ["sz", "aec"]
        self.cpp_info.set_property("cmake_file_name", "libsz")
        self.cpp_info.set_property("cmake_target_name", "libsz::libsz")
        self.cpp_info.set_property("pkg_config_name", "libsz")
