#!/usr/bin/env python3
"""Conan test_package — libcuckoo-acp 0.3.1 consumer test.

Builds test_libcuckoo_acp.cpp against the packaged headers and runs 10 real
API checks (insert/find/erase/update/upsert/locked_table/clear/throwing
find). The binary's "LIBCUCKOO_ACP_TEST total=N passed=M" summary line is the
single counting source for HMBS_TEST_PACKAGE_RESULT. The build-time upstream
evidence (res/hmbs_upstream_result.json) is re-emitted every run so cache-hit
rounds still carry both HMBS markers in the log.

CI runs this automatically via `conan create` (which invokes test_package).
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment

# Consumer checks compiled into test_libcuckoo_acp.cpp.
CONSUMER_TOTAL = 10


class LibcuckooAcpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # E092 applies to the consumer as well: without an explicit system
        # name the consumer configures as unknown platform ("System is
        # unknown to cmake"). Pin Linux via cache_variables (emitted as -D).
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Mirror the main recipe compiler fallback: the shared profile may
        # pin a compiler path missing on this runner, so resolve
        # tool-specifically and pin the working one. Healthy machines
        # keep zero behaviour change.
        try:
            _compilers = self.conf.get("tools.build:compiler_executables",
                                       default=None)
        except Exception:
            _compilers = None
        if not isinstance(_compilers, dict):
            _compilers = {}
        _c = self._resolve_compiler(_compilers.get("c"), ("clang", "cc"))
        _cxx = self._resolve_compiler(_compilers.get("cpp"),
                                      ("clang++", "c++"))
        if _c:
            tc.cache_variables["CMAKE_C_COMPILER"] = _c
        if _cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        self.output.info("HMBS diag test compilers c=%s cxx=%s" % (_c, _cxx))
        tc.generate()
        CMakeDeps(self).generate()
        self._fix_generated_toolchain_compiler(_compilers, _c, _cxx)

    def _resolve_compiler(self, configured, names):
        if configured and os.path.exists(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local",
                                "bin")
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.exists(cand):
                return cand
        return configured or names[0]

    def _fix_generated_toolchain_compiler(self, configured_map, c, cxx):
        # Same guard as the main recipe: only rewrite when the configured
        # path is confirmed missing and the resolved one exists.
        if not isinstance(configured_map, dict):
            configured_map = {}
        c_old = configured_map.get("c")
        cxx_old = configured_map.get("cpp")
        pairs = []
        if c_old and c and c_old != c \
                and not os.path.exists(c_old) and os.path.exists(c):
            pairs.append((c_old, c))
        if cxx_old and cxx and cxx_old != cxx \
                and not os.path.exists(cxx_old) and os.path.exists(cxx):
            pairs.append((cxx_old, cxx))
        if not pairs:
            return
        try:
            gf = getattr(self, "generators_folder", None)
            path = os.path.join(gf, "conan_toolchain.cmake") if gf else None
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8",
                          errors="replace") as f:
                    text = f.read()
                orig = text
                for old_p, new_p in pairs:
                    text = text.replace(old_p, new_p)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    self.output.info(
                        "HMBS diag test fixed toolchain %s" % path)
            else:
                self.output.warning(
                    "HMBS diag test toolchain not found: %s" % path)
        except Exception as e:
            self.output.warning("HMBS diag test toolchain fix failed: %s" % e)
        try:
            comp_env = Environment()
            if c_old and c and (c_old, c) in pairs:
                comp_env.define("CC", c)
            if cxx_old and cxx and (cxx_old, cxx) in pairs:
                comp_env.define("CXX", cxx)
            comp_env.vars(self, scope="build").save_sh("hmbs_compiler")
        except Exception as e:
            self.output.warning("HMBS diag test compiler env failed: %s" % e)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException(
                "libcuckoo-acp consumer test is not runnable on this configuration")
        cmake = CMake(self)
        cmake.test()
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libcuckoo_acp")
        if not os.path.isfile(binary):
            raise ConanException("consumer test binary missing: %s" % binary)
        log_path = os.path.join(self.build_folder, "test_libcuckoo_acp.log")
        # Catch-record-continue-then-raise: always parse the log for the
        # marker first, then fail loudly if the run was not fully green.
        returncode = 0
        try:
            self.run('"%s" > "%s" 2>&1' % (binary, log_path), env="conanrun")
        except ConanException:
            returncode = 1
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        self.output.info("consumer test output:\n%s" % out[-3000:])
        discovered = CONSUMER_TOTAL
        passed_count = 0
        summary = re.search(r"LIBCUCKOO_ACP_TEST total=(\d+) passed=(\d+)", out)
        if summary:
            discovered = int(summary.group(1))
            passed_count = int(summary.group(2))
        ok = (returncode == 0 and summary is not None
              and discovered == CONSUMER_TOTAL and passed_count == CONSUMER_TOTAL)
        marker = {
            "executed": True,
            "passed": bool(ok),
            "command": "./test_libcuckoo_acp (insert/find/erase/update/upsert/locked_table/clear/throw)",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        if summary is None:
            marker["detail"] = "summary line missing in consumer output; binary rc=%d" % returncode
        line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(line, flush=True)
        self.output.info(line)
        self._reemit_upstream()
        if not ok:
            raise ConanException(
                "libcuckoo-acp consumer test failed: passed=%d/%d rc=%d" % (
                    passed_count, discovered, returncode))

    def _reemit_upstream(self):
        # Re-emit the build-time upstream evidence every run; missing or
        # invalid evidence fails loudly instead of silently dropping it.
        for dep in self.dependencies.values():
            candidate = os.path.join(
                str(dep.package_folder), "res", "hmbs_upstream_result.json")
            if not os.path.isfile(candidate):
                continue
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError) as exc:
                raise ConanException(
                    "invalid upstream evidence %s: %s" % (candidate, exc))
            if not isinstance(data, dict) or data.get("status") not in (
                    "passed", "failed"):
                raise ConanException(
                    "upstream evidence has illegal status: %s" % data)
            for key in ("discovered", "executed", "passed", "failed", "skipped"):
                if not isinstance(data.get(key), int) or data[key] < 0:
                    raise ConanException(
                        "upstream evidence has illegal counts: %s" % data)
            if not (data["passed"] + data["failed"] == data["executed"]
                    and data["executed"] <= data["discovered"]
                    and data["executed"] + data["skipped"] <= data["discovered"]):
                raise ConanException(
                    "upstream evidence counts contradictory: %s" % data)
            if data["status"] != "passed":
                # Only a documented gaps entry justifies re-emitting a
                # non-green suite: gaps must be present, well-formed, use
                # allowed categories, and sum to discovered - passed.
                gaps = data.get("gaps")
                if not isinstance(gaps, list) or not gaps:
                    raise ConanException(
                        "upstream evidence not green and no gaps: %s" % data)
                total_gap = 0
                for gap in gaps:
                    if not isinstance(gap, dict):
                        raise ConanException(
                            "upstream evidence has malformed gap: %s" % data)
                    count = gap.get("count")
                    category = gap.get("category")
                    if not isinstance(count, int) or count <= 0:
                        raise ConanException(
                            "upstream evidence has illegal gap count: %s"
                            % data)
                    if category not in ("environment", "ohos_feature",
                                        "test_failure"):
                        raise ConanException(
                            "upstream evidence has illegal gap category: %s"
                            % data)
                    if not gap.get("detail") or not gap.get("evidence"):
                        raise ConanException(
                            "upstream evidence gap lacks detail/evidence: %s"
                            % data)
                    total_gap += count
                if total_gap != data["discovered"] - data["passed"]:
                    raise ConanException(
                        "upstream evidence gaps do not cover shortfall: %s"
                        % data)
            line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data, ensure_ascii=False)
            print(line, flush=True)
            self.output.info(line)
            return
        raise ConanException(
            "upstream evidence res/hmbs_upstream_result.json not found in package")
