#!/usr/bin/env python3
"""Conan test_package for tsduck 4676 - Conan L1 official test.

Consumer view (8 checks, each counted from real output, never exit-0-alone):
  * test_tsduck binary (CMake, links tsduck::tsduck): 6 "CHECK-OK:" lines
    from real libtsduck API calls (version macros, TSPacket init/PID/CC,
    UString) - see test_tsduck.cpp.
  * CLI: "tsversion --version" output must contain "3.44-4676".
  * CLI: "tsp -I file data/null10.ts -O file <out>" round-trips 10 null
    packets byte-identical (1880 bytes) through the real plugin pipeline
    (file input/output plugins are built into libtsduck).

Upstream evidence: the TSUnit suite runs in the main recipe build() and
persists res/hmbs_upstream.json in the package, so this re-emits
HMBS_UPSTREAM_TEST_RESULT from that file on every run (cache-hit rounds
skip the main build, the gate still needs the marker).
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy


# test_tsduck.cpp prints exactly 6 "CHECK-OK:" lines, one per API check.
API_CHECK_COUNT = 6
# CLI checks below: tsversion version string + tsp file round-trip.
CLI_CHECK_COUNT = 2
TOTAL_CHECKS = API_CHECK_COUNT + CLI_CHECK_COUNT


class TsduckTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def configure(self):
        # Upstream requires C++20 (tsIntegerUtils.h uses concept/requires/
        # std::integral); the repo profile pins cppstd=17, so force 20 for
        # this consumer (baloo/kcoreaddons precedent).
        try:
            self.settings.compiler.cppstd = "20"
        except Exception:
            pass

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # The profile pins cppstd=17: drop the baked block and force C++20
        # (baloo 6.28.0 precedent; CMAKE_CXX_STANDARD alone is overridden
        # by the toolchain's own cppstd block, hence remove + explicit flags).
        try:
            tc.blocks.remove("cppstd")
        except Exception:
            pass
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_EXTENSIONS"] = "OFF"
        tc.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"
        tc.generate()
        VirtualRunEnv(self).generate()
        self._fix_toolchain_compilers()

    def _resolve_compiler(self, key, fallbacks):
        """Working compiler for key ('c'/'cpp'), plus the searched evidence.

        The repo OHOS profile nails tools.build:compiler_executables to an
        absolute path that is missing on some preflight runners (this round:
        CMake errors 'No CMAKE_CXX_COMPILER could be found' for
        /data/service/hnp/bin/clang++ while the main make build compiled
        fine via its own PATH fallback). Same rule as the main recipe:
        conf path wins when it exists, otherwise first PATH hit.
        """
        searched = []
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={},
                check_type=dict) or {}
        except Exception:
            executables = {}
        configured = executables.get(key) if isinstance(executables, dict) else None
        if configured:
            searched.append("conf:%s" % configured)
            if os.path.isfile(configured):
                return configured, searched
        for name in fallbacks:
            searched.append("which:%s" % name)
            found = shutil.which(name)
            if found and os.path.isfile(found):
                return found, searched
        return "", searched

    def _fix_toolchain_compilers(self):
        """Replace nonexistent compiler paths baked into conan_toolchain.cmake.

        CMakeToolchain copies the profile compiler path verbatim; when that
        file is absent on the runner, cmake.configure() dies with 'No
        CMAKE_CXX_COMPILER could be found' before compiling anything. Patch
        only confirmed-missing paths (existence check, never touch healthy
        machines); when no working compiler exists at all, fail fast with
        the searched evidence so it routes as infra, not a recipe bug.
        """
        wanted = {
            "CXX": self._resolve_compiler("cpp", ["clang++", "c++"]),
            "C": self._resolve_compiler("c", ["clang", "cc"]),
        }
        toolchains = []
        for root, _dirs, files in os.walk(self.build_folder):
            if "conan_toolchain.cmake" in files:
                toolchains.append(os.path.join(root, "conan_toolchain.cmake"))
        if not toolchains:
            raise ConanException(
                "conan_toolchain.cmake not found under %s; "
                "cannot verify test_package compilers" % self.build_folder)
        for path in toolchains:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            original = text
            for lang, (resolved, searched) in wanted.items():
                pattern = re.compile(
                    r"^(.*CMAKE_%s_COMPILER[^\n\"]*\")([^\n\"]+)(\".*)$"
                    % lang, re.MULTILINE)
                match = pattern.search(text)
                if not match:
                    self.output.info(
                        "test_package: no CMAKE_%s_COMPILER line in %s"
                        % (lang, path))
                    continue
                baked = match.group(2)
                if os.path.isfile(baked):
                    self.output.info(
                        "test_package: CMAKE_%s_COMPILER keeps %s (exists)"
                        % (lang, baked))
                    continue
                if not resolved:
                    raise ConanException(
                        "test_package needs a working %s compiler: profile "
                        "path %s missing and PATH has no fallback "
                        "(searched: %s)" % (lang, baked, " | ".join(searched)))
                self.output.warning(
                    "test_package: CMAKE_%s_COMPILER %s missing on this "
                    "runner, using %s instead (searched: %s)"
                    % (lang, baked, resolved, " | ".join(searched)))
                text = (text[:match.start()] + match.group(1) + resolved
                        + match.group(3) + text[match.end():])
            if text != original:
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
                self.output.info("test_package: patched %s" % path)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # make_jobserver_fifo: HMDFS has no GNU make FIFO jobserver; keep the
        # tiny consumer build serial (tools.build:jobs=1, --parallel 1).
        try:
            cmake.build(cli_args=["--parallel", "1"])
        except Exception:
            cmake.build()

    def _bin(self, name):
        pkg = self.dependencies["tsduck"].package_folder
        path = os.path.join(pkg, "bin", name)
        if not os.path.isfile(path):
            raise ConanException("packaged binary missing: %s" % path)
        return path

    def _run_capture(self, cmd, cwd):
        """Run cmd via a shell redirect; return (returncode, output text)."""
        logfile = os.path.join(self.build_folder, "tp-capture.log")
        if os.path.isfile(logfile):
            os.remove(logfile)
        returncode = 0
        try:
            # stale_runtime_library fix (preflight 2026-10-01: tsp dies with
            # `symbol not found` because the test process loads the system old
            # lib instead of the just-built package). Prepend the current
            # package lib dir to LD_LIBRARY_PATH AND LD_PRELOAD the exact
            # packaged .so files for this test command only (OHOS loader may
            # ignore LD_LIBRARY_PATH). Same pattern as the main-recipe
            # TSPLUGINS_PATH/LD_LIBRARY_PATH=bindir for utest.
            prefix = self._pkg_lib_env_prefix()
            # POSIX sh is enough here (no bash-isms in the commands).
            self.run('%s%s > "%s" 2>&1' % (prefix, cmd, logfile), cwd=cwd, env="conanrun")
        except Exception:
            returncode = 1
        text = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        return returncode, text

    def _pkg_lib_env_prefix(self):
        """Shell prefix forcing this test command onto the packaged libs."""
        try:
            pkg = self.dependencies["tsduck"].package_folder
        except Exception:
            return ""
        libdir = os.path.join(pkg, "lib")
        parts = []
        if os.path.isdir(libdir):
            parts.append('LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH"' % libdir)
        preloads = []
        for name in ("libtsduck.so", "libtscore.so"):
            cand = os.path.join(libdir, name)
            if os.path.isfile(cand):
                preloads.append(cand)
        if preloads:
            parts.append('LD_PRELOAD="%s"' % " ".join(preloads))
        if not parts:
            return ""
        return " ".join(parts) + " "

    def test(self):
        if not can_run(self):
            return
        passed = 0

        # 1) C++ API consumer: count CHECK-OK lines (each = one real check).
        consumer = os.path.join(self.cpp.build.bindir, "test_tsduck")
        if not os.path.isfile(consumer):
            raise ConanException("test binary missing: %s" % consumer)
        rc, out = self._run_capture('"%s"' % consumer, self.build_folder)
        self.output.info("----- test_tsduck output -----\n" + out)
        api_ok = len(re.findall(r"^CHECK-OK: \S+", out, re.MULTILINE))
        api_fail = len(re.findall(r"^CHECK-FAIL: ", out, re.MULTILINE))
        if rc == 0 and api_fail == 0 and api_ok == API_CHECK_COUNT:
            passed += api_ok
        else:
            self.output.error(
                "test_tsduck failed: rc=%d ok=%d fail=%d (want %d)" %
                (rc, api_ok, api_fail, API_CHECK_COUNT))

        # 2) CLI: tsversion must report the adapted upstream version.
        rc, out = self._run_capture('"%s" --version' % self._bin("tsversion"),
                                    self.build_folder)
        self.output.info("----- tsversion output -----\n" + out)
        if rc == 0 and "3.44-4676" in out:
            passed += 1
        else:
            self.output.error("tsversion check failed: rc=%d" % rc)

        # 3) CLI: tsp file-to-file round-trip of data/null10.ts (10 null
        # packets, 1880 bytes) must come back byte-identical.
        workdir = os.path.join(self.build_folder, "tsp-work")
        os.makedirs(workdir, exist_ok=True)
        fixture = os.path.join(self.source_folder, "data", "null10.ts")
        if not os.path.isfile(fixture):
            raise ConanException("test fixture missing: %s" % fixture)
        out_ts = os.path.join(workdir, "out.ts")
        if os.path.isfile(out_ts):
            os.remove(out_ts)
        tsp = self._bin("tsp")
        plugins = os.path.join(self.dependencies["tsduck"].package_folder,
                               "lib", "tsduck")
        rc, out = self._run_capture(
            'TSPLUGINS_PATH="%s" "%s" -I file "%s" -O file "%s"'
            % (plugins, tsp, fixture, out_ts), workdir)
        self.output.info("----- tsp output -----\n" + out)
        identical = (
            rc == 0 and os.path.isfile(out_ts)
            and os.path.getsize(out_ts) == os.path.getsize(fixture)
            and open(out_ts, "rb").read() == open(fixture, "rb").read())
        if identical:
            passed += 1
        else:
            self.output.error("tsp round-trip check failed: rc=%d" % rc)

        result = {
            "executed": True,
            "passed": passed == TOTAL_CHECKS,
            "command": "./test_tsduck + tsversion --version + tsp file round-trip",
            "discovered": TOTAL_CHECKS,
            "passedCount": passed,
        }
        marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result)
        print(marker, flush=True)
        self.output.info(marker)
        self._reemit_upstream()
        if passed != TOTAL_CHECKS:
            raise ConanException(
                "test_package failed: %d/%d checks passed" % (passed, TOTAL_CHECKS))

    def _reemit_upstream(self):
        try:
            dep = self.dependencies["tsduck"]
            cand = os.path.join(dep.package_folder, "res", "hmbs_upstream.json")
            if os.path.isfile(cand):
                with open(cand, "r", encoding="utf-8") as handle:
                    up = json.load(handle)
                up_marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                    up, ensure_ascii=False)
                print(up_marker, flush=True)
                self.output.info(up_marker)
            else:
                self.output.warning(
                    "hmbs_upstream.json absent from package res/; "
                    "upstream marker left to the main build (cache-miss rounds)")
        except Exception as exc:
            self.output.warning("upstream re-emit failed: %s" % exc)
