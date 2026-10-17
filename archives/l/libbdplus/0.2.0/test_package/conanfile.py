#!/usr/bin/env python3
"""Conan test_package — libbdplus 0.2.0 consumer test.

Builds test_bdplus.c against the packaged library (CMakeDeps +
CMakeToolchain), runs it on the native OHOS target and counts the
per-check "CHECK-OK:" lines for the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker (exit-0-alone is not proof: 4 CHECK-OK lines
are required for a pass).

Upstream evidence: libbdplus 0.2.0 ships no automated test harness
(audit in MANIFEST.yml), so this re-emits HMBS_UPSTREAM_TEST_RESULT
with status=no_tests on every run (cache-hit rounds skip the main
build, the gate still needs the marker).
"""

import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, cmake_layout

# test_bdplus.c performs exactly 4 checks, each printing one
# "CHECK-OK: <name>" line on success.
CONSUMER_CHECK_COUNT = 4


class LibbdplusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        # HMBS injects a task-private writable TMPDIR on the real
        # machine; prefer it in every phase and fall back to a dir
        # under build_folder so neither CMake nor the test binary
        # touches a possibly read-only /tmp.
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                tmp = candidate
                break
        else:
            tmp = None
        if not tmp:
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        return tmp

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _emit_upstream_marker(self):
        upstream_marker = {
            "status": "no_tests",
            "framework": "autotools-make-check",
            "command": "make check (upstream provides no automated suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "libbdplus 0.2.0 ships no automated test harness: "
                "no TEST/TEST_F, no ctest/meson/pytest wiring, no automake "
                "TESTS/check_PROGRAMS and no make check target "
                "(src/examples/ holds only manual noinst programs); "
                "see test_package/MANIFEST.yml upstream_test_audit"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )

    def test(self):
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building: compile/link test completed")
            self._emit_upstream_marker()
            return
        self._ensure_writable_tmp()
        self._run_consumer_binary(raise_on_failure=True)
        # Prove the binary also executes under the conanrun environment
        # (shared .so resolves via runenv LD_LIBRARY_PATH). OHOS shells
        # may not exec ELF directly, so drive it through CONFIG_SHELL
        # bash like the zlib precedent. Explicit LD_LIBRARY_PATH/LD_PRELOAD
        # prefix keeps this second run working even when the loader ignores
        # the runenv path (xeyes stale_runtime_library precedent).
        import shlex as _shlex
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_bdplus")
        _rt = self._runtime_env()
        _prefix = "LD_LIBRARY_PATH=%s LD_PRELOAD=%s " % (
            _shlex.quote(_rt.get("LD_LIBRARY_PATH", "")),
            _shlex.quote(_rt.get("LD_PRELOAD", ""))) if _rt.get(
                "LD_LIBRARY_PATH") or _rt.get("LD_PRELOAD") else ""
        self.run('%s -c "%s%s"' % (bash, _prefix, bin_path), env="conanrun")
        self._emit_upstream_marker()
        self.output.info("libbdplus consumer test_package passed")

    def _runtime_libdirs(self):
        # Collect dependency + own-package lib dirs for LD_LIBRARY_PATH.
        # subprocess.run bypasses the conanrun env, so an explicit path is
        # required on OHOS where the loader has no default search for the
        # Conan cache (httperf/gnutls precedent).
        dirs = []
        for name in ("libbdplus", "libgcrypt", "libgpg-error"):
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            for libdir in dep.cpp_info.libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(
                    str(dep.package_folder), libdir)
                if os.path.isdir(path) and path not in dirs:
                    dirs.append(path)
        return dirs

    def _find_so(self, dep, prefix):
        hits = []
        for root, _dirs, files in os.walk(str(dep.package_folder)):
            for f in sorted(files):
                if f.startswith(prefix):
                    hits.append(os.path.join(root, f))
        if not hits:
            return None
        for p in hits:
            if not os.path.islink(p):
                return p
        return hits[0]

    def _runtime_preload(self):
        # HMBS [stale_runtime_library]: the OHOS loader may ignore
        # LD_LIBRARY_PATH for non-system namespaces; point LD_PRELOAD at
        # the just-built shared objects by absolute path (xeyes precedent).
        # Dependency order: libgpg-error -> libgcrypt -> libbdplus.
        found = []
        for name, prefix in (("libgpg-error", "libgpg-error.so.0"),
                             ("libgcrypt", "libgcrypt.so.20"),
                             ("libbdplus", "libbdplus.so.0")):
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            so = self._find_so(dep, prefix)
            if so:
                found.append(so)
        return ":".join(found)

    def _runtime_env(self):
        env = dict(os.environ)
        libdirs = self._runtime_libdirs()
        if libdirs:
            prior = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = ":".join(libdirs) + (
                (":" + prior) if prior else "")
        preload = self._runtime_preload()
        if preload:
            self.output.info("runtime LD_PRELOAD=%s" % preload)
            env["LD_PRELOAD"] = preload + (
                (":" + env["LD_PRELOAD"]) if env.get("LD_PRELOAD") else "")
        return env

    def _run_consumer_binary(self, raise_on_failure):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_bdplus")
        if not os.path.isfile(bin_path):
            raise ConanException("test binary missing: %s" % bin_path)
        proc = subprocess.run(
            [bin_path],
            env=self._runtime_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        output = proc.stdout or ""
        self.output.info(output[-2000:])
        ok_count = output.count("CHECK-OK:")
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and ok_count == CONSUMER_CHECK_COUNT,
            "command": bin_path,
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not marker["passed"] and raise_on_failure:
            raise ConanException(
                "consumer test failed: rc=%s ok=%s/%s"
                % (proc.returncode, ok_count, CONSUMER_CHECK_COUNT)
            )
