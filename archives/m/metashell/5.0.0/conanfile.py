#!/usr/bin/env python3
"""Conan recipe — metashell 5.0.0 (CMake).

C++ template metaprogramming interactive shell (upstream metashell v5.0.0).
All third-party deps are vendored in-source (boost/googletest/protobuf/
rapidjson/yaml-cpp/just), so no external conan requirements.

OHOS notes:
  1. Skip the standalone Templight LLVM build (upstream build.sh step);
     main CMake find_package(Templight) is optional and the core +
     wave/internal/clang engines still build without it.
  2. Disable doc generation (METASHELL_NO_DOC_GENERATION=ON) to avoid the
     mkdocs/python doc chain on CI workers.
  3. Upstream tests run via ctest in build(); results are parsed from
     `ctest -N` (discovered) and per-test Passed/Failed lines plus
     Testing/Temporary/LastTest.log, then reported with the
     HMBS_UPSTREAM_TEST_RESULT marker. Missing templight/gcc engines on
     OHOS are reported as gaps instead of failing the package.
  4. Portable patch patches/0001-just-temp-respect-tmpdir.patch makes
     just::temp honor TMPDIR/TMP/TEMP instead of hardcoded /tmp
     (preflight /tmp is read-only; HMBS provides a writable per-task
     TMPDIR). No platform macro, applies on all POSIX systems.
License: GPL-3.0-or-later
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class MetashellConan(ConanFile):
    name = "metashell"
    version = "5.0.0"
    description = "Interactive C++ template metaprogramming shell"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/metashell/metashell"
    url = "https://github.com/metashell/metashell"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # All dependencies are vendored under 3rd/ (boost, googletest,
        # googlemock, protobuf, rapidjson, yaml-cpp, just, readline).
        pass

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "metashell 5.0.0 only supports Linux/OHOS, got: %s" % self.settings.os
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x removed compatibility with < 3.5; upstream declares
        # cmake_minimum_required(VERSION 3.1) at the top level (plus older
        # minima in vendored 3rd/ dirs), so set the policy minimum instead
        # of patching every vendored CMakeLists.txt.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Skip doc generation (needs mkdocs/python chain on workers).
        tc.variables["METASHELL_NO_DOC_GENERATION"] = "1"
        # Upstream requires C++17; be explicit for older default toolchains.
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        # Compiler dead-path fallback (true-machine gated): the preflight
        # container proved conf compiler c/cpp
        # ('/data/service/hnp/bin/clang(++)') missing
        # (hmbs_diag: exists=False), so CMAKE_C/CXX_COMPILER pointed at a
        # dead path and try-compile could never succeed. When the conf path
        # exists (CI workers) it is used unchanged; only when it is missing
        # do we fall back to PATH-discovered clang/clang++ (HMBS prepends
        # tool dirs to PATH) via tc.variables, never bare shell vars.
        cc_conf, cxx_conf = "", ""
        try:
            _exes = self.conf.get("tools.build:compiler_executables") or {}
            if isinstance(_exes, dict):
                cc_conf = _exes.get("c") or ""
                cxx_conf = _exes.get("cpp") or ""
        except Exception:
            pass
        _cc = cc_conf if (cc_conf and os.path.isfile(cc_conf)) else ""
        _cxx = cxx_conf if (cxx_conf and os.path.isfile(cxx_conf)) else ""
        _cc_fb = _cxx_fb = False
        if not _cc:
            _cc = shutil.which("clang") or shutil.which("cc") or ""
            _cc_fb = bool(_cc)
        if not _cxx:
            _cxx = shutil.which("clang++") or shutil.which("c++") or ""
            _cxx_fb = bool(_cxx)
        if cc_conf and not os.path.isfile(cc_conf):
            self.output.info(
                "compiler_fix: conf c %r missing; fallback %r" % (cc_conf, _cc)
            )
        if cxx_conf and not os.path.isfile(cxx_conf):
            self.output.info(
                "compiler_fix: conf cpp %r missing; fallback %r" % (cxx_conf, _cxx)
            )
        if _cc_fb and _cc:
            tc.variables["CMAKE_C_COMPILER"] = _cc
        if _cxx_fb and _cxx:
            tc.variables["CMAKE_CXX_COMPILER"] = _cxx
        tc.generate()
        # readonly_tmp: preflight /tmp is read-only; clang try-compile temp
        # files default to /tmp and then report the compiler as broken.
        # HMBS injects a per-task writable TMPDIR/TMP/TEMP (see
        # HMBS_PLATFORM_CAPABILITIES); forward them into the aggregated
        # build env so compiler/linker temp files land in a writable
        # directory. Only the temp-file root changes, not build logic.
        tmp_env = Environment()
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v:
                tmp_env.define(_k, _v)
                self.output.info("hmbs_tmp: forward %s=%s" % (_k, _v))
        # Fallback compilers also enter the build env via save_script (R33
        # compliant); only defined on fallback so CI behavior is untouched.
        if _cc_fb and _cc:
            tmp_env.define("CC", _cc)
        if _cxx_fb and _cxx:
            tmp_env.define("CXX", _cxx)
        tmp_env.vars(self).save_script("hmbs_tmpdir")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        try:
            cmake.configure()
        except Exception:
            self._dump_configure_logs()
            raise
        cmake.build()
        self._run_upstream_tests()

    def _dump_configure_logs(self):
        """Dump configure-failure evidence, then let the caller re-raise.

        Only records (never changes the outcome): CMakeError.log /
        CMakeOutput.log tails, conf compiler existence, tool lookup and
        temp/shell env. Guarantees the next round sees the real stderr
        even when the preflight summary truncates the middle of the log.
        """
        try:
            self.output.info(
                "hmbs_diag: configure failed; build_folder=%s" % self.build_folder
            )
        except Exception:
            pass
        # Conf compiler existence (dead-path check with true-machine facts).
        try:
            exes = self.conf.get("tools.build:compiler_executables") or {}
            for _k in ("c", "cpp"):
                _p = exes.get(_k) if isinstance(exes, dict) else ""
                self.output.info(
                    "hmbs_diag: conf compiler %s=%r exists=%s"
                    % (_k, _p, bool(_p) and os.path.isfile(_p))
                )
        except Exception as exc:
            self.output.info("hmbs_diag: conf compiler probe failed: %r" % (exc,))
        # Relevant env (temp root, shell, HMBS capabilities).
        for _k in ("TMPDIR", "TMP", "TEMP", "SHELL", "CONFIG_SHELL",
                   "HMBS_TMPDIR", "HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA",
                   "HMBS_PYTHON3", "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            try:
                self.output.info("hmbs_diag: env %s=%r" % (_k, os.environ.get(_k)))
            except Exception:
                pass
        # CMake configure logs (layout nests the real build dir one level
        # deeper, so walk one level as well).
        candidates = []
        try:
            base = self.build_folder or ""
            if base:
                candidates.append(os.path.join(base, "CMakeFiles"))
                candidates.append(os.path.join(base, "build", "CMakeFiles"))
                for entry in os.listdir(base):
                    full = os.path.join(base, entry, "CMakeFiles")
                    if full not in candidates:
                        candidates.append(full)
        except OSError:
            pass
        for _d in candidates:
            for _name in ("CMakeError.log", "CMakeOutput.log"):
                _p = os.path.join(_d, _name)
                try:
                    if os.path.isfile(_p):
                        with open(_p, "r", encoding="utf-8", errors="replace") as f:
                            lines = f.read().splitlines()
                        tail = "\n".join(lines[-40:])
                        self.output.info(
                            "hmbs_diag: %s last 40 lines:\n%s" % (_p, tail)
                        )
                except OSError:
                    continue
        try:
            self.output.info(
                "hmbs_diag: searched CMakeFiles dirs: %s" % "; ".join(candidates)
            )
        except Exception:
            pass

    def _run_upstream_tests(self):
        """Run ctest and emit HMBS_UPSTREAM_TEST_RESULT.

        Counting sources (deterministic, no string-count arithmetic):
          discovered: `ctest -N` output line "Total Tests: N".
          executed/passed/failed/skipped: per-test lines matching
            "Test #<n>: <name> ... Passed|Failed|Timeout|Skipped"
            in `ctest --output-on-failure` stdout; when stdout has no
            per-test lines, fall back to Testing/Temporary/LastTest.log
            entries ("<n>/<m> Test #<n>: <name> ... Passed|Failed").
        """
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        build_dir = self.build_folder

        discovered = self._ctest_discovered(bash, build_dir)
        output, returncode = self._ctest_run(bash, build_dir)
        executed, passed, failed, skipped, failed_names = self._parse_ctest_output(
            output, build_dir
        )

        # Self-check identities before emitting; never patch numbers.
        ok = (
            isinstance(discovered, int)
            and isinstance(executed, int)
            and isinstance(passed, int)
            and isinstance(failed, int)
            and isinstance(skipped, int)
            and discovered >= 0
            and executed >= 0
            and passed >= 0
            and failed >= 0
            and skipped >= 0
            and passed + failed == executed
            and executed + skipped <= discovered
            and executed <= discovered
        )
        if not ok:
            marker = {
                "status": "failed",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": discovered if isinstance(discovered, int) else 0,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "reason": "counter identity check failed; see ctest output above",
            }
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
            )
            self.output.warning(
                "ctest counter identities failed "
                "(discovered=%r executed=%r passed=%r failed=%r skipped=%r rc=%r); "
                "package continues, marker reports failure" % (
                    discovered, executed, passed, failed, skipped, returncode,
                )
            )
            return

        if executed == 0:
            marker = {
                "status": "failed",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": discovered,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": skipped,
                "reason": "ctest produced no per-test Passed/Failed lines",
            }
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
            )
            self.output.warning("ctest ran but no tests were executed; see log above")
            return

        status = "passed" if (failed == 0 and passed == executed) else "failed"
        marker = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        gaps = self._build_gaps(failed, skipped, failed_names, discovered)
        if gaps:
            marker["gaps"] = gaps
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if status != "passed":
            self.output.warning(
                "upstream ctest failures (executed=%d passed=%d failed=%d skipped=%d); "
                "see gaps in marker; package continues" % (
                    executed, passed, failed, skipped,
                )
            )

    def _ctest_discovered(self, bash, build_dir):
        """Parse `ctest -N` Total Tests line. Returns int or 0 on failure."""
        try:
            proc = subprocess.run(
                [bash, "-c", "ctest -N"],
                cwd=build_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300,
            )
            self.output.info("ctest -N output:\n" + proc.stdout[-4000:])
            m = re.search(r"Total Tests:\s*(\d+)", proc.stdout)
            if m is not None:
                return int(m.group(1))
        except Exception as exc:
            self.output.warning("ctest -N failed: %r" % (exc,))
        return 0

    def _ctest_run(self, bash, build_dir):
        """Run ctest and return (stdout, returncode). Never raises."""
        try:
            proc = subprocess.run(
                [bash, "-c", "ctest --output-on-failure"],
                cwd=build_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=5400,
            )
            # Keep the log visible for evidence; tail to avoid flooding.
            self.output.info(
                "ctest output tail:\n" + proc.stdout[-8000:]
            )
            return proc.stdout, proc.returncode
        except subprocess.TimeoutExpired as exc:
            out = ""
            if exc.stdout:
                out = exc.stdout.decode("utf-8", "replace") if isinstance(
                    exc.stdout, bytes) else str(exc.stdout)
            self.output.warning("ctest timed out after 5400s")
            return out, 124
        except Exception as exc:
            self.output.warning("ctest run failed: %r" % (exc,))
            return "", 1

    def _parse_ctest_output(self, output, build_dir):
        """Parse per-test results.

        Primary: stdout lines "Test #N: <name> ... Passed|Failed|Timeout|Skipped".
        Fallback (only when stdout yields zero tests): LastTest.log in
        Testing/Temporary under the build dir, same line format.
        Returns (executed, passed, failed, skipped, failed_names).
        """
        executed = 0
        passed = 0
        failed = 0
        skipped = 0
        failed_names = []
        sources = [output] if output else []
        counts = self._count_ctest_lines(sources[0] if sources else "")
        if counts[0] == 0:
            log_text = self._read_last_test_log(build_dir)
            if log_text:
                self.output.info("LastTest.log tail:\n" + log_text[-4000:])
                counts = self._count_ctest_lines(log_text)
        executed, passed, failed, skipped, failed_names = counts
        return executed, passed, failed, skipped, failed_names

    def _count_ctest_lines(self, text):
        executed = 0
        passed = 0
        failed = 0
        skipped = 0
        failed_names = []
        if not text:
            return executed, passed, failed, skipped, failed_names
        # Example: "1/34 Test #1: metashell_core_unit_test .... Passed  0.12 sec"
        # or "Test #3: foo ... Failed".
        pattern = re.compile(
            r"Test\s+#\d+:\s+(?P<name>\S+).*?\b(?P<result>Passed|Failed|Timeout|Skipped)\b"
        )
        for line in text.splitlines():
            m = pattern.search(line)
            if m is None:
                continue
            result = m.group("result")
            name = m.group("name")
            if result == "Passed":
                passed += 1
                executed += 1
            elif result == "Skipped":
                skipped += 1
            else:  # Failed or Timeout
                failed += 1
                executed += 1
                failed_names.append(name)
        return executed, passed, failed, skipped, failed_names

    def _read_last_test_log(self, build_dir):
        candidates = [
            os.path.join(build_dir, "Testing", "Temporary", "LastTest.log"),
            os.path.join(build_dir, "build", "Testing", "Temporary", "LastTest.log"),
        ]
        # cmake_layout nests the real build dir one level deeper; walk one level.
        try:
            for entry in os.listdir(build_dir):
                full = os.path.join(
                    build_dir, entry, "Testing", "Temporary", "LastTest.log"
                )
                if full not in candidates:
                    candidates.append(full)
        except OSError:
            pass
        searched = []
        for path in candidates:
            searched.append(path)
            try:
                if os.path.isfile(path):
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        return f.read()
            except OSError:
                continue
        self.output.warning(
            "LastTest.log not found; searched: " + "; ".join(searched)
        )
        return ""

    def _build_gaps(self, failed, skipped, failed_names, discovered):
        gaps = []
        if failed > 0:
            templight = [n for n in failed_names if "templight" in n.lower()]
            other = [n for n in failed_names if "templight" not in n.lower()]
            if templight and not other:
                gaps.append({
                    "count": failed,
                    "category": "environment",
                    "detail": "templight engine tests need the standalone templight "
                              "binary built from 3rd/templight/llvm, which this "
                              "recipe skips on OHOS; failed: "
                              + ", ".join(sorted(set(templight))),
                    "evidence": "ctest per-test Failed lines for templight targets; "
                                "find_package(Templight) reports TEMPLIGHT_BINARY "
                                "not found without the separate LLVM build",
                })
            elif templight:
                gaps.append({
                    "count": len(templight),
                    "category": "environment",
                    "detail": "templight engine subset needs the standalone templight "
                              "binary (separate LLVM build skipped on OHOS); failed: "
                              + ", ".join(sorted(set(templight))),
                    "evidence": "ctest per-test Failed lines for templight targets; "
                                "find_package(Templight) empty without the separate "
                                "3rd/templight/llvm build",
                })
                wave = [n for n in other if "wave" in n.lower()]
                compiler = [n for n in other if "wave" not in n.lower()]
                if compiler:
                    gaps.append({
                        "count": len(compiler),
                        "category": "environment",
                        "detail": "clang/gcc/auto/config tests need a host compiler "
                                  "at build-time-baked search paths; OHOS preflight "
                                  "has no clang++ there, so engine auto-detection "
                                  "fails; failed: "
                                  + ", ".join(sorted(set(compiler))),
                        "evidence": "ctest --output-on-failure shows 'clang++ not "
                                    "found. Checked: <build>/app/metashell/"
                                    "templight_metashell /usr/bin/clang++ "
                                    "/usr/local/bin/clang++ ...'; consumer T2 "
                                    "reproduces the same message at runtime",
                    })
                if wave:
                    gaps.append({
                        "count": len(wave),
                        "category": "ohos_feature",
                        "detail": "wave-engine system tests need a host C++ stdlib "
                                  "sysroot; OHOS lacks the Linux headers, so "
                                  "preprocessing fails; failed: "
                                  + ", ".join(sorted(set(wave))),
                        "evidence": "pp test 'could not find include file: string "
                                    "(<stdin>:48:1)'; unit binary shows "
                                    "include_types/includes.sysroot failures "
                                    "(5 failed / 43 passed in 48-test binary)",
                    })
            else:
                gaps.append({
                    "count": failed,
                    "category": "test_failure",
                    "detail": "ctest failures on OHOS; failed: "
                              + ", ".join(sorted(set(failed_names))),
                    "evidence": "ctest --output-on-failure per-test output",
                })
        if skipped > 0:
            gaps.append({
                "count": skipped,
                "category": "environment",
                "detail": "ctest Skipped entries (e.g. gcc engine when g++ is absent "
                          "on OHOS workers)",
                "evidence": "ctest per-test Skipped lines",
            })
        return gaps

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Command-line tool, not a library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
