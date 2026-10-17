#!/usr/bin/env python3
"""Conan test_package for xerces 3.3.0 — Conan L1 official test.

Uses CMake (CMakeDeps + CMakeToolchain) so the compiler is driven by the
Conan toolchain, not raw shell env vars (R33). The consumer test feeds an
in-memory XML document to XercesDOMParser and asserts on the parsed DOM
tree (no errors, document non-null, root element, root tag, element count,
text content — 6 assertions).

Evidence markers (HMBS rule4 hard gates):
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "CHECK PASS:" / "CHECK FAIL:" lines of the test binary output. Those
  lines are the single deterministic counting source (one line per
  assertion, anchored prefix match, no arithmetic patch-ups); the marker
  is emitted via both print() and self.output.info() every run.
- HMBS_UPSTREAM_TEST_RESULT: re-emitted verbatim from the upstream
  evidence carried in the package (res/upstream_test_result.json, written
  by the main recipe build() after running ctest). Re-emission keeps
  evidence available on cache-hit rounds where build() is skipped; a
  missing evidence file raises instead of faking a marker.
"""

import glob
import json
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

# test.cpp prints exactly one "CHECK PASS:" / "CHECK FAIL:" line per
# assertion; 6 assertions in total.
EXPECTED_ASSERTIONS = 6


class XercesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _conf_compilers(self):
        # Same helper as the main recipe: read profile-declared compilers
        # without probing executability (no os.access/X_OK: HMDFS
        # misreports; existence via isfile only).
        try:
            conf = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            conf = {}
        c = conf.get("c", "") if isinstance(conf, dict) else ""
        cpp = conf.get("cpp", "") if isinstance(conf, dict) else ""
        return (c.strip() if isinstance(c, str) else ""), \
               (cpp.strip() if isinstance(cpp, str) else "")

    def _fallback_compiler(self, lang):
        # Same candidates as the main recipe: hnp bin dir first (profile
        # authority), then versioned SDK llvm bin dirs, then PATH (hmbs
        # prepends its tool dirs, e.g. harmonybrew clang which proved good
        # in the main build).
        base = "clang" if lang == "c" else "clang++"
        cands = ["/data/service/hnp/bin/%s" % base]
        cands += sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/%s" % base))
        found = shutil.which(base)
        if found:
            cands.append(found)
        for cand in cands:
            if cand and os.path.isfile(cand):
                return cand
        return ""

    def generate(self):
        # Same toolchain form as the main recipe (barrier-2.4.0 proven
        # pattern): plain variables, Linux alias for the missing
        # Platform/HarmonyOS module. Consumer configure also runs
        # project() under CMake 4.4.3, so it needs the same alias.
        # Plus the same compiler fallback: the profile-declared
        # /data/service/hnp/bin/clang++ fails identification on this
        # worker while the harmonybrew clang used by the main build
        # succeeds; pin the fallback explicitly when the conf path is
        # absent, otherwise keep profile authority untouched.
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        c_conf, cpp_conf = self._conf_compilers()
        c_ok = bool(c_conf) and os.path.isfile(c_conf)
        cpp_ok = bool(cpp_conf) and os.path.isfile(cpp_conf)
        self.output.info("conf compilers: c=%s(exists=%s) cpp=%s(exists=%s)"
                         % (c_conf or "<empty>", c_ok,
                            cpp_conf or "<empty>", cpp_ok))
        if not (c_ok and cpp_ok):
            c_fb = self._fallback_compiler("c") if not c_ok else ""
            cpp_fb = self._fallback_compiler("cpp") if not cpp_ok else ""
            self.output.info("compiler fallback: c=%s cpp=%s"
                             % (c_fb or "<none>", cpp_fb or "<none>"))
            if c_fb:
                tc.variables["CMAKE_C_COMPILER"] = c_fb
            if cpp_fb:
                tc.variables["CMAKE_CXX_COMPILER"] = cpp_fb
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _find_test_binary(self):
        """Locate the built test_xerces executable under the build folder."""
        names = ("test_xerces", "test_xerces.exe")
        hits = []
        for root, _dirs, files in os.walk(self.build_folder):
            for name in names:
                if name in files:
                    hits.append(os.path.join(root, name))
        if not hits:
            raise ConanException(
                "test_xerces binary not found under build folder %s "
                "(harness broken)" % self.build_folder)
        # Prefer the CTest-registered executable at the build root.
        hits.sort(key=len)
        self.output.info("test binary: %s" % hits[0])
        return hits[0]

    def _emit(self, line):
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: consumer compiled and linked")
            return
        exe = self._find_test_binary()
        # R5: OHOS has no /bin/sh — drive execution through CONFIG_SHELL.
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL")
                 or "/bin/sh")
        logfile = os.path.join(self.build_folder, "test_package.log")
        cmd = "%s > %s 2>&1" % (shlex.quote(exe), shlex.quote(logfile))
        # ignore_errors=True so the log is always parsed and the marker is
        # always emitted; failure is reported below with real counts.
        self.run("%s -c %s" % (shell, shlex.quote(cmd)),
                 env="conanrun", ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8",
                      errors="replace") as f:
                out = f.read()
        for line in out.splitlines()[-12:]:
            self.output.info("[test-xerces] %s" % line)

        # Single deterministic source: one anchored line per assertion.
        passed = len(re.findall(r"^CHECK PASS:", out, re.MULTILINE))
        failed = len(re.findall(r"^CHECK FAIL:", out, re.MULTILINE))
        executed = passed + failed
        if executed != EXPECTED_ASSERTIONS:
            raise ConanException(
                "test_xerces evidence broken: %d CHECK lines found, "
                "expected %d (passed=%d failed=%d). Full log: %s"
                % (executed, EXPECTED_ASSERTIONS, passed, failed, logfile))
        ok = (failed == 0 and passed == EXPECTED_ASSERTIONS)
        tp_marker = {
            "executed": True,
            "passed": ok,
            "command": "./test_xerces",
            "discovered": EXPECTED_ASSERTIONS,
            "passedCount": passed,
        }
        self._emit("HMBS_TEST_PACKAGE_RESULT=%s"
                   % json.dumps(tp_marker, separators=(",", ":")))

        # Re-emit the real upstream result carried in the package so
        # cache-hit rounds still provide evidence every round.
        try:
            res = os.path.join(
                self.dependencies["xerces"].package_folder,
                "res", "upstream_test_result.json")
            with open(res, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if not (payload.get("status") == "passed"
                    and int(payload.get("discovered", 0)) > 0
                    and int(payload.get("executed", 0)) > 0):
                raise ConanException(
                    "upstream evidence invalid, refusing to re-emit: %s"
                    % payload)
            self._emit("HMBS_UPSTREAM_TEST_RESULT=%s"
                       % json.dumps(payload, separators=(",", ":")))
        except ConanException:
            raise
        except Exception as exc:
            raise ConanException(
                "upstream evidence res/upstream_test_result.json missing "
                "or unreadable, refusing to fake it: %s" % exc)

        if not ok:
            raise ConanException(
                "test_xerces failed: %d/%d assertions failed"
                % (failed, EXPECTED_ASSERTIONS))
        self.output.info("xerces consumer test_package passed")
