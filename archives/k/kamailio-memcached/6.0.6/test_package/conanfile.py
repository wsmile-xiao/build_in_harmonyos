#!/usr/bin/env python3
"""Conan test_package — kamailio-memcached 6.0.6 consumer test.

The package ships `lib/kamailio/modules/memcached.so`, a Kamailio module that
the Kamailio host loads with dlopen().  The consumer harness therefore plays
the host (kamailio_host_stubs.c is linked -rdynamic, exactly like the Kamailio
binary) and dlopen()s the *packaged* module:

  * resolves the module's own exported interface table (`exports`) and checks
    that its first member `name` equals "memcached" (`struct module_exports`);
  * calls into the libmemcached code statically embedded in the module
    (`memcached_lib_version()` returns "1.0.18"; `memcached_create`/
    `memcached_free` are usable);
  * asserts the OHOS-specific properties of the delivered ELF: the object is
    ELF64/AArch64, DT_NEEDED contains only the OHOS system runtime
    (`libc.so`, `libc++_shared.so`), no build-machine RPATH/RUNPATH leaked,
    and the Kamailio core ABI stays host-provided (left undefined) while no
    `memcached_*` symbol is left undefined.

The harness prints one "CHECK-OK: <name>" line per passed assertion (10 in
total, 4 of them OHOS-specific); the count is reported through
HMBS_TEST_PACKAGE_RESULT so exit-0 alone is never taken as proof.
"""

import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

# test_memcached_module.c performs exactly 10 checks.
CONSUMER_CHECK_COUNT = 10


class KamailioMemcachedTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _module_path(self):
        dep = self.dependencies[self.tested_reference_str]
        return os.path.join(str(dep.package_folder), "lib", "kamailio",
                            "modules", "memcached.so")

    def _ensure_writable_tmp(self):
        # /tmp may be read-only on the device; prefer the environment's
        # writable temp dir, else a directory under build_folder.
        tmp = None
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                tmp = candidate
                break
        if not tmp:
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        return tmp

    def generate(self):
        self._ensure_writable_tmp()
        module_so = self._module_path()
        self.output.info("packaged module: %s" % module_so)
        if not os.path.isfile(module_so):
            raise ConanException(
                "packaged module not found: %s" % module_so)
        tc = CMakeToolchain(self)
        tc.cache_variables["MODULE_SO"] = module_so
        tc.generate()

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _test_binary(self):
        return os.path.join(self.cpp.build.bindirs[0], "test_memcached_module")

    def _run_consumer_binary(self):
        bin_path = self._test_binary()
        if not os.path.isfile(bin_path):
            raise ConanException("test binary missing: %s" % bin_path)
        proc = subprocess.run(
            [bin_path],
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        output = proc.stdout or ""
        self.output.info(output[-4000:])
        return proc.returncode, output

    def test(self):
        if cross_building(self):
            # Nothing to execute on a foreign host: emit the markers explicitly
            # so the round is never left without a machine-readable verdict.
            self.output.info("cross-building: compile/link test completed")
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(
                    {"executed": False, "passed": False, "skipped": True,
                     "reason": "cross-building: consumer binary not runnable",
                     "command": self._test_binary(),
                     "discovered": CONSUMER_CHECK_COUNT, "passedCount": 0},
                    ensure_ascii=False))
            self._emit_upstream_marker()
            return
        self._ensure_writable_tmp()
        cmake = CMake(self)
        try:
            cmake.test()
        except Exception as exc:
            # Keep the real evidence instead of losing it, and still emit the
            # machine marker so the harness can judge the round.
            self.output.warning("ctest failed: %s" % exc)
            rc, output = self._run_consumer_binary()
            self._emit_marker(rc, output, executed=True)
            self._emit_upstream_marker()
            raise

        rc, output = self._run_consumer_binary()
        self._emit_marker(rc, output, executed=True)
        # L0d: prove the binary also executes under the conanrun environment.
        self.run(self._test_binary(), env="conanrun")
        self._emit_upstream_marker()
        self.output.info("kamailio-memcached consumer test_package passed")

    def _emit_marker(self, rc, output, executed):
        ok_count = output.count("CHECK-OK:")
        marker = {
            "executed": executed,
            "passed": rc == 0 and ok_count == CONSUMER_CHECK_COUNT,
            "command": self._test_binary(),
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if not marker["passed"]:
            raise ConanException(
                "consumer test failed: rc=%s ok=%s/%s"
                % (rc, ok_count, CONSUMER_CHECK_COUNT))

    def _emit_upstream_marker(self):
        # Kamailio 6.0.6 ships no test suite; the upstream entry point is the
        # build entry.  See 6.0.6/reports/upstream-test-audit.md.
        upstream_marker = {
            "status": "no_upstream_test_suite",
            "framework": "none",
            "command": "make -C src modules modules=modules/memcached",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "Kamailio 6.0.6 has no automated test suite: no top-level "
                "test/ directory, no tests in src/modules/memcached, no "
                "make check/TESTS target in the Makefile hierarchy, and the "
                "in-tree Alpine APKBUILD declares options=\"!check\" "
                "(no testsuite).  The real upstream entry point is the build "
                "entry make modules modules=modules/memcached, which this "
                "recipe executes.  See reports/upstream-test-audit.md."
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False))
