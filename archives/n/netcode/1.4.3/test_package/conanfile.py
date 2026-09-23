#!/usr/bin/env python3
"""Conan test_package -- netcode 1.4.3.

Consumer test (test_netcode, 4 TAP sub-tests against the packaged library)
plus a rerun of the upstream suite binary persisted under
res/upstream-test by the main recipe.

Both HMBS markers are emitted on every run so evidence survives Conan
cache hits (build() may be skipped when the package is already cached).
"""
import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

# Audited at v1.4.3: 46 RUN_TEST() cases in netcode.c netcode_test()
# (NETCODE_PACKET_TAGGING defaults to 1 on non-MinGW targets, OHOS included).
EXPECTED_UPSTREAM_TESTS = 46

# Consumer TAP plan emitted by test_package/test.c (1..4).
EXPECTED_CONSUMER_TESTS = 4


class NetcodeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _resolve_compiler(self, key, fallbacks):
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict) or {}
        except Exception:
            executables = {}
        cand = executables.get(key)
        if cand:
            if os.path.isabs(cand):
                try:
                    if os.path.isfile(cand) and os.access(cand, os.X_OK):
                        return cand
                except OSError:
                    pass
            else:
                found = shutil.which(cand)
                if found:
                    return found
                return cand
        for name in fallbacks:
            found = shutil.which(name)
            if found:
                return found
        return cand or fallbacks[0]

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_C_COMPILER"] = self._resolve_compiler("c", ("clang", "cc"))
        tc.variables["CMAKE_CXX_COMPILER"] = self._resolve_compiler("cpp", ("clang++", "c++"))
        tc.generate()

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _ensure_writable_tmp(self):
        """OHOS /tmp is read-only: reuse HMBS TMPDIR, else build tmp."""
        candidate = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )

        def _writable(path):
            try:
                os.makedirs(path, exist_ok=True)
                probe = os.path.join(path, ".hmbs_write_probe")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("ok")
                try:
                    os.remove(probe)
                except OSError:
                    pass
                return True
            except OSError:
                return False

        if candidate and _writable(candidate):
            tmp = candidate
        else:
            try:
                base = self.build_folder
            except Exception:
                base = os.path.expanduser("~")
            tmp = os.path.join(base, "tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        return tmp

    def _find_consumer(self):
        patterns = ("test_netcode", "test_netcode.exe")
        search_dirs = list(self.cpp.build.bindirs)
        search_dirs.append(self.build_folder)
        for directory in search_dirs:
            if not directory or not os.path.isdir(directory):
                continue
            for name in patterns:
                cand = os.path.join(directory, name)
                if os.path.isfile(cand):
                    return cand
        for root, _dirs, files in os.walk(self.build_folder):
            for name in patterns:
                if name in files:
                    return os.path.join(root, name)
        return None

    def _check_consumer_output(self, out):
        if not out.strip():
            raise ConanException("consumer test produced no output, refusing to pass")
        header = re.search(r"^1\.\.(\d+)\s*$", out, re.MULTILINE)
        if not header:
            raise ConanException("consumer TAP plan line (1..N) missing, refusing to pass")
        discovered = int(header.group(1))
        ok_names = re.findall(r"^ok\s+\d+\s+-\s+(.+)$", out, re.MULTILINE)
        not_ok = re.findall(r"^not ok\s+\d+", out, re.MULTILINE)
        passed = len(ok_names) if not not_ok and len(ok_names) == discovered else 0
        return discovered, passed, not not_ok and discovered == EXPECTED_CONSUMER_TESTS

    def _find_upstream_runner(self):
        dep = self.dependencies["netcode"]
        base = os.path.join(dep.package_folder, "res", "upstream-test")
        for name in ("test", "test.exe"):
            cand = os.path.join(base, name)
            if os.path.isfile(cand):
                return cand
        found = glob.glob(os.path.join(base, "test*"))
        return found[0] if found else None

    def test(self):
        if not can_run(self):
            self.output.warning("can_run is False, skipping runtime checks")
            return
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.test()

        consumer = self._find_consumer()
        if consumer is None:
            raise ConanException("consumer test binary test_netcode not found")
        # Falsification guard: a stub binary must never count as a pass.
        if os.path.getsize(consumer) < 1024:
            raise ConanException("consumer test binary too small, refusing: %s" % consumer)

        log_path = os.path.join(self.build_folder, "consumer_test.log")
        with open(log_path, "w", encoding="utf-8") as log_file:
            self.run('"%s"' % consumer, env="conanrun", stdout=log_file)
        with open(log_path, "r", encoding="utf-8", errors="replace") as log_file:
            consumer_out = log_file.read()
        self.output.info("consumer test output:\n" + consumer_out)

        discovered, passed, plan_ok = self._check_consumer_output(consumer_out)
        consumer_ok = plan_ok and passed == discovered
        tp_marker = {
            "executed": True,
            "passed": consumer_ok,
            "command": "test_netcode (consumer TAP)",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker))
        if not consumer_ok:
            raise ConanException("consumer test failed: %s" % json.dumps(tp_marker))

        runner = self._find_upstream_runner()
        if runner is None:
            marker = {
                "status": "failed",
                "framework": "ctest",
                "command": "test (upstream netcode_test rerun from package res/)",
                "discovered": EXPECTED_UPSTREAM_TESTS,
                "executed": 0,
                "passed": 0,
                "failed": EXPECTED_UPSTREAM_TESTS,
                "skipped": 0,
                "reason": "upstream runner missing under res/upstream-test",
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
            raise ConanException("upstream runner missing under res/upstream-test")
        try:
            os.chmod(runner, 0o755)
        except OSError:
            pass
        if os.path.getsize(runner) < 1024:
            raise ConanException("upstream runner too small, refusing: %s" % runner)

        proc = subprocess.run(
            [runner],
            cwd=self.build_folder,
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=900,
        )
        out = proc.stdout or ""
        self.output.info("upstream rerun output:\n" + out)
        if not out.strip():
            raise ConanException("upstream rerun produced no output, refusing to pass")
        seen = {n.strip() for n in re.findall(r"^\s*(?:\d+:\s*)?(test_[A-Za-z0-9_]+)\s*$", out, re.MULTILINE)}
        executed = len(seen)
        banner = "*** ALL TESTS PASSED ***" in out
        # The rerun prints exactly the RUN_TEST names; all 46 must appear.
        ok = proc.returncode == 0 and banner and executed == EXPECTED_UPSTREAM_TESTS
        marker = {
            "status": "passed" if ok else "failed",
            "framework": "ctest",
            "command": "test (upstream netcode_test rerun from package res/)",
            "discovered": EXPECTED_UPSTREAM_TESTS,
            "executed": executed,
            "passed": executed if ok else 0,
            "failed": 0 if ok else EXPECTED_UPSTREAM_TESTS,
            "skipped": 0,
        }
        if not ok:
            marker["reason"] = "rc=%d banner=%s executed=%d/%d" % (
                proc.returncode, banner, executed, EXPECTED_UPSTREAM_TESTS)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        if not ok:
            raise ConanException("upstream rerun failed: %s" % json.dumps(marker))
