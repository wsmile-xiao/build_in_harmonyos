#!/usr/bin/env python3
"""Installed-package consumer test for libofa 0.9.3.

Builds and runs one program that links against the *packaged* headers and
library and exercises the whole public C API from include/ofa1/ofa.h:
library version reporting and end-to-end fingerprint generation
(ofa_create_print) on synthetic PCM, including output validity and
determinism across calls.

The program prints one "PLAN <n>" line followed by one "CHECK-OK: <name>"
line per passing check; those lines are the deterministic source for the
HMBS_TEST_PACKAGE_RESULT machine-evidence marker (exit-0-alone is not
proof). Upstream itself ships no test suite (see test_package/MANIFEST.yml),
so this consumer test is the functional gate.
"""

import io
import json
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


# test_libofa.c performs exactly 6 checks, each printing one
# "CHECK-OK: <name>" line on success, preceded by a "PLAN 6" line.
CONSUMER_PLAN = 6


class LibofaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _try_compile(self, compiler, source):
        """True if *compiler* really compiles+links a trivial program.

        Same ground-truth rule as the main recipe probes: never trust
        existence/X_OK (HMDFS ignores chmod, X_OK is always False), only
        a real compile+link. Failures only return False; details go to
        the preflight log.
        """
        try:
            tmp = tempfile.mkdtemp(prefix="hmbs-tp-probe-")
        except OSError as error:
            self.output.info("tp compiler probe: mkdtemp failed (%s)" % error)
            return False
        is_cxx = source.strip().startswith("int main(){")
        src = os.path.join(tmp, "probe.cpp" if is_cxx else "probe.c")
        exe = os.path.join(tmp, "probe")
        try:
            with open(src, "w") as handle:
                handle.write(source)
        except OSError as error:
            self.output.info("tp compiler probe: cannot write source (%s)" % error)
            return False
        try:
            proc = subprocess.run([compiler, src, "-o", exe],
                                  capture_output=True, text=True, timeout=180)
        except Exception as error:
            self.output.info("tp compiler probe: %s not launchable (%s)"
                             % (compiler, error))
            return False
        if proc.returncode == 0 and os.path.isfile(exe):
            return True
        self.output.info("tp compiler probe: %s FAILED rc=%d"
                         % (compiler, proc.returncode))
        for line in ((proc.stderr or "").splitlines()[:10]):
            self.output.info("tp compiler probe stderr | %s" % line[:300])
        return False

    def _working_compilers(self):
        """Resolve working C/CXX compilers, profile-first with fallback.

        Root cause of the failed round: CMakeToolchain bakes the profile's
        tools.build:compiler_executables (/data/service/hnp/bin/clang)
        into the test_package toolchain, but on the preflight host that
        hnp path is not launchable while the working cross clang lives on
        PATH (harmonybrew). The main recipe already probes CC/CXX this
        way; the test_package CMake step needs the same treatment or
        cmake.configure() dies with 'CMAKE_C_COMPILER ... is not able to
        compile'. Candidate order is profile conf first (so official CI,
        where hnp exists, keeps using it), then CC/CXX env, then the
        sibling clang++ next to a verified CC, then PATH lookup. Only a
        candidate that really compiles+links is returned.
        """
        try:
            executables = self.conf.get("tools.build:compiler_executables",
                                        default={}) or {}
        except Exception:
            executables = {}
        c_candidates = []
        if isinstance(executables, dict):
            value = executables.get("c")
            if value and str(value) not in c_candidates:
                c_candidates.append(str(value))
        value = os.environ.get("CC")
        if value and value not in c_candidates:
            c_candidates.append(value)
        for name in ("clang", "cc", "gcc"):
            found = shutil.which(name)
            if found and found not in c_candidates:
                c_candidates.append(found)
        self.output.info("tp compiler probe: C candidates %s" % c_candidates)
        c_src = "int main(void){return 0;}\n"
        working_cc = None
        for candidate in c_candidates:
            if self._try_compile(candidate, c_src):
                try:
                    ver = subprocess.run(
                        [candidate, "--version"], capture_output=True,
                        text=True, timeout=60).stdout.splitlines()
                except Exception:
                    ver = []
                self.output.info("tp compiler probe: CC %s OK%s"
                                 % (candidate,
                                    (" (%s)" % ver[0][:100]) if ver else ""))
                working_cc = candidate
                break
        cxx_candidates = []
        if isinstance(executables, dict):
            value = executables.get("cpp")
            if value and str(value) not in cxx_candidates:
                cxx_candidates.append(str(value))
        if working_cc:
            for sibling in (os.path.join(os.path.dirname(working_cc), "clang++"),
                            os.path.join(os.path.dirname(working_cc), "g++")):
                if sibling not in cxx_candidates:
                    cxx_candidates.append(sibling)
        value = os.environ.get("CXX")
        if value and value not in cxx_candidates:
            cxx_candidates.append(value)
        for name in ("clang++", "c++", "g++"):
            found = shutil.which(name)
            if found and found not in cxx_candidates:
                cxx_candidates.append(found)
        self.output.info("tp compiler probe: CXX candidates %s" % cxx_candidates)
        cxx_src = "int main(){return 0;}\n"
        working_cxx = None
        for candidate in cxx_candidates:
            if self._try_compile(candidate, cxx_src):
                self.output.info("tp compiler probe: CXX %s OK" % candidate)
                working_cxx = candidate
                break
        if working_cc is None and working_cxx is not None:
            # Reverse sibling fallback: CXX hit (harmonybrew clang++)
            # proves the toolchain dir works, so derive CC from it even
            # if the C candidate list missed (e.g. PATH lookup gap).
            for sibling in (os.path.join(os.path.dirname(working_cxx), "clang"),
                            os.path.join(os.path.dirname(working_cxx), "cc"),
                            os.path.join(os.path.dirname(working_cxx), "gcc")):
                if self._try_compile(sibling, c_src):
                    self.output.info("tp compiler probe: CC %s OK (via CXX sibling)"
                                     % sibling)
                    working_cc = sibling
                    break
        if working_cc is None:
            self.output.info("tp compiler probe: no working C compiler; "
                             "leaving toolchain as-is")
        if working_cxx is None:
            self.output.info("tp compiler probe: no working CXX compiler; "
                             "leaving toolchain as-is")
        return working_cc, working_cxx

    def _patch_cmake_toolchain_compilers(self, cc, cxx):
        """Rewrite compiler paths inside the generated conan_toolchain.cmake.

        Round-3 lesson: neither tc.cache_variables (round 1) nor
        cmake.configure(variables={...}) -D flags (round 2) overrode the
        profile's hnp compiler -- the generated conan_toolchain.cmake kept
        baking /data/service/hnp/bin/clang and CMake kept failing on it
        (the toolchain set() wins over preset/command-line cache
        variables). So patch the generated file itself in build(), right
        before cmake.configure(): replace the quoted path of each
        set(CMAKE_C_COMPILER ...)/set(CMAKE_CXX_COMPILER ...) line with
        the probe-verified binary, preserving the rest of the line
        (CACHE/FORCE suffix untouched). Only verified compile+link
        binaries are written; anything unexpected only logs and leaves
        the file alone so the real CMake error stays visible.
        """
        if not cc and not cxx:
            self.output.info("tp toolchain patch: no verified compilers; skipping")
            return
        path = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(path):
            self.output.info("tp toolchain patch: not found: %s" % path)
            return
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError as error:
            self.output.info("tp toolchain patch: cannot read %s (%s)" % (path, error))
            return
        for var, new in (("CMAKE_C_COMPILER", cc), ("CMAKE_CXX_COMPILER", cxx)):
            if not new:
                continue
            old = re.findall(r'set\(' + var + r'\s+"([^"]*)"', text)
            self.output.info("tp toolchain patch: %s before=%s after=%s" % (var, old, new))

            def _repl(match, _new=new):
                return match.group(1) + _new + match.group(2)
            text, count = re.subn(r'(set\(' + var + r'\s+")[^"]*(")',
                                  _repl, text)
            self.output.info("tp toolchain patch: %s replaced %d line(s)" % (var, count))
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
        except OSError as error:
            self.output.info("tp toolchain patch: cannot write %s (%s)" % (path, error))

    def generate(self):
        working_cc, working_cxx = self._working_compilers()
        tc = CMakeToolchain(self)
        # Pin probe-verified compilers so the generated toolchain does not
        # point at the profile's hnp path when it is not launchable here.
        # Profile-first ordering keeps official CI (hnp present) unchanged.
        if working_cc:
            tc.cache_variables["CMAKE_C_COMPILER"] = working_cc
        if working_cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = working_cxx
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        # NOTE (rounds 1-2): neither tc.cache_variables nor
        # cmake.configure(variables={...}) -D flags overrode the profile's
        # hnp compiler -- the generated conan_toolchain.cmake kept baking
        # /data/service/hnp/bin/clang. Keep the -D flags and additionally
        # rewrite the generated toolchain file itself (see below).
        working_cc, working_cxx = self._working_compilers()
        toolchain_vars = {}
        if working_cc:
            toolchain_vars["CMAKE_C_COMPILER"] = working_cc
        if working_cxx:
            toolchain_vars["CMAKE_CXX_COMPILER"] = working_cxx
        if toolchain_vars:
            self.output.info("tp build: pinning CMake compilers %s"
                             % toolchain_vars)
        # Round 3: -D flags alone lost to the toolchain set() in round 2,
        # so rewrite the generated conan_toolchain.cmake itself as well.
        self._patch_cmake_toolchain_compilers(working_cc, working_cxx)
        cmake = CMake(self)
        cmake.configure(variables=toolchain_vars)
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException(
                "libofa consumer binary cannot run on this platform")
        executable = os.path.join(self.cpp.build.bindir, "test_libofa")
        if not os.path.isfile(executable):
            raise ConanException("test binary missing: %s" % executable)
        stream = io.StringIO()
        return_code = 0
        try:
            self.run('"%s"' % executable, env="conanrun",
                     stdout=stream, stderr=stream)
        except ConanException as exc:
            self.output.warning("test_libofa exited non-zero: %s" % exc)
            return_code = 1
        output = stream.getvalue()
        for line in output.splitlines():
            if line.startswith(("PLAN ", "CHECK-OK:", "CHECK-FAIL:")):
                self.output.info("  | %s" % line)
        plan = 0
        for line in output.splitlines():
            if line.startswith("PLAN "):
                try:
                    plan = int(line.split()[1])
                except (IndexError, ValueError):
                    plan = 0
                break
        discovered = plan
        passed_count = sum(1 for line in output.splitlines()
                           if line.startswith("CHECK-OK:"))
        passed = (return_code == 0 and discovered == CONSUMER_PLAN
                  and passed_count == discovered)
        tp_result = {
            "executed": True,
            "passed": passed,
            "command": "./test_libofa",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        tp_marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result)
        print(tp_marker, flush=True)
        self.output.info(tp_marker)
        if not passed:
            raise ConanException(
                "test_libofa failed (plan=%d, check-ok=%d, rc=%d)"
                % (discovered, passed_count, return_code))
        # Upstream has no test suite (audited: no tests/ dir, no TESTS in
        # any Makefile.am - see MANIFEST.yml upstream_test_audit).
        # Re-emit the no_tests evidence every run so the gate passes even
        # on Conan cache hits where the main build() is skipped. This
        # mirrors the merged bwm/0.6.3 no_tests precedent
        # (upstream_test_in_build: false path).
        upstream_marker = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": ("libofa 0.9.3 upstream has no test suite: no tests/ "
                       "directory, no TESTS assignment in any of the 7 "
                       "Makefile.am files (autotools_tests count 0); "
                       "examples/ only holds noinst MusicDNS demo clients, "
                       "not a test suite; automake check target is a no-op"),
        }
        up_msg = ("HMBS_UPSTREAM_TEST_RESULT="
                  + json.dumps(upstream_marker, separators=(",", ":")))
        print(up_msg, flush=True)
        self.output.info(up_msg)
