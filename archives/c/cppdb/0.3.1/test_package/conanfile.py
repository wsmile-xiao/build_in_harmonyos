#!/usr/bin/env python3
"""Conan test_package — cppdb 0.3.1.

Builds two binaries against the packaged library and runs them:
- test_cppdb: consumer test (public frontend API over sqlite).
- test_cppdb_upstream: replay of the offline-capable upstream
  test_basic/test_backend sqlite paths (no DB server needed).

Both binaries print one OK line per passing check; the counts are parsed
into the HMBS machine-evidence markers below. Markers are emitted from
test() (not only from the main build()) so evidence also exists on
conan-cache-hit rounds where build() is skipped. Any mismatch raises.
"""
import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

CONSUMER_CHECKS = 6
UPSTREAM_CHECKS = 20


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _find_bin(self, name):
        for d in self.cpp.build.bindirs:
            cand = os.path.join(d, name)
            if os.path.isfile(cand):
                return cand
        for root, _, files in os.walk(self.build_folder):
            if name in files:
                return os.path.join(root, name)
        return None

    def _run_env(self):
        # Test binaries link the packaged shared libraries in shared mode;
        # give the loader the package libdirs explicitly (static default
        # mode needs nothing extra, this is harmless there).
        env = dict(os.environ)
        # HarmonyOS preflight mounts /tmp read-only; point sqlite (and any
        # libc mktemp path) at the HMBS-injected writable TMPDIR. Only the
        # temp-file root is redirected, no test is skipped.
        tmpdir = (env.get("TMPDIR") or env.get("TMP") or env.get("TEMP") or "").strip()
        if tmpdir and os.path.isdir(tmpdir):
            env["SQLITE_TMPDIR"] = tmpdir
        paths = []
        for name in ("cppdb", "sqlite3"):
            try:
                dep = self.dependencies[name]
            except Exception:
                continue
            for attr in ("bindirs", "libdirs"):
                for p in getattr(dep.cpp_info, attr, []) or []:
                    ap = p if os.path.isabs(p) else os.path.join(dep.package_folder, p)
                    if os.path.isdir(ap) and ap not in paths:
                        paths.append(ap)
        if paths:
            old = env.get("LD_LIBRARY_PATH")
            env["LD_LIBRARY_PATH"] = ":".join(paths) + (":" + old if old else "")
        return env

    def _run_and_log(self, binary, args):
        log = os.path.join(self.build_folder, os.path.basename(binary) + ".log")
        # Route sqlite temp files at the HMBS writable TMPDIR via the
        # process environment so self.run(env="conanrun") inherits it.
        run_env = self._run_env()
        saved = {}
        for k in ("SQLITE_TMPDIR", "TMPDIR", "TMP", "TEMP", "LD_LIBRARY_PATH"):
            saved[k] = os.environ.get(k)
            if run_env.get(k):
                os.environ[k] = run_env[k]
        # Run the real test binary via self.run (L0d gate requires it)
        # and capture output through shell redirect (portable across
        # Conan 2.x: only cwd/env/ignore_errors params are used).
        cmd = " ".join([shlex.quote(binary)] + [shlex.quote(a) for a in args])
        cmd = cmd + " > " + shlex.quote(log) + " 2>&1"
        try:
            rc = self.run(cmd, cwd=self.build_folder, env="conanrun",
                          ignore_errors=True)
            rc = int(rc) if rc is not None else 0
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        with open(log, "r", encoding="utf-8", errors="replace") as f:
            out = f.read()
        self.output.info("test output %s:\n%s" % (os.path.basename(binary), out))
        return rc, out

    def test(self):
        if not can_run(self):
            return
        consumer = self._find_bin("test_cppdb")
        replay = self._find_bin("test_cppdb_upstream")
        if not consumer or not replay:
            raise ConanException("test binaries not found: %s / %s" % (consumer, replay))

        rc, out = self._run_and_log(
            consumer, [os.path.join(self.build_folder, "test_pkg.db")])
        found = len(re.findall(r"^CHECK-OK ", out, re.MULTILINE))
        consumer_ok = (rc == 0 and found == CONSUMER_CHECKS
                       and "CONSUMER-ALL-OK" in out)
        marker = {
            "executed": True,
            "passed": consumer_ok,
            "command": "test_cppdb (sqlite CRUD over packaged cppdb)",
            "discovered": CONSUMER_CHECKS,
            "passedCount": found if consumer_ok else 0,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        if not consumer_ok:
            raise ConanException("consumer test failed: rc=%d checks=%d/%d"
                                 % (rc, found, CONSUMER_CHECKS))

        rc, out = self._run_and_log(
            replay, [os.path.join(self.build_folder, "test_upstream.db")])
        found = len(re.findall(r"^UPSTREAM-OK ", out, re.MULTILINE))
        replay_ok = (rc == 0 and found == UPSTREAM_CHECKS
                     and "UPSTREAM-ALL-OK" in out)
        upstream = {
            "status": "passed" if replay_ok else "failed",
            "framework": "custom",
            "command": "test_cppdb_upstream (replay of upstream test_basic/test_backend sqlite paths)",
            "discovered": UPSTREAM_CHECKS,
            "executed": UPSTREAM_CHECKS,
            "passed": found if replay_ok else 0,
            "failed": 0 if replay_ok else UPSTREAM_CHECKS,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))
        if not replay_ok:
            raise ConanException("upstream replay failed: rc=%d checks=%d/%d"
                                 % (rc, found, UPSTREAM_CHECKS))
        self.output.info("cppdb test_package passed")
