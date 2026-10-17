#!/usr/bin/env python3
"""Conan test_package — libnids 1.26 consumer test.

Builds test_nids.c against the packaged libnids (CMakeDeps +
CMakeToolchain), runs it on the native OHOS target and counts the
per-check "CHECK-OK:" lines for the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker (exit-0-alone is not proof: 6 CHECK-OK lines
are required for a pass).

Upstream evidence: libnids 1.26 ships no automated test harness
(no make check target, no tests/ dir, no ctest/gtest/pytest wiring;
samples/ are manual root/network programs), so this emits
HMBS_UPSTREAM_TEST_RESULT with status=no_tests on every run.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


CONSUMER_CHECK_COUNT = 6


class LibnidsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # nids.h publicly includes <pcap.h>: declare libpcap directly so
        # CMakeDeps always emits the Conan libpcap config (previous round
        # linked libpcap::libpcap in CMakeLists alone but left libpcap
        # transitive-only, and the 12:51 preflight still failed with
        # 'pcap.h file not found'). Pinned to the same version the main
        # recipe requires, so no override conflict.
        self.requires("libpcap/1.10.6")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # OHOS-adapted Conan maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS,
        # but vanilla CMake has no Platform/HarmonyOS.cmake (only
        # Platform/OHOS.cmake), so the configure step warns
        # "System is unknown to cmake" and the compiler check
        # (/data/service/hnp/bin/clang simple test program) fails.
        # Align with Platform/OHOS.cmake like fmt/12.2.0 + stringzilla/5.1.2
        # test_package precedent (E092).
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Main-recipe evidence: profile compiler
        # /data/service/hnp/bin/clang is not executable from /bin/sh on
        # this worker (earlier "inaccessible or not found"); the Autotools
        # build succeeded only after probing a working CC (harmonybrew
        # clang via PATH). CMakeToolchain otherwise pins the same broken
        # absolute path, so CMake's compiler identification fails even
        # with the OHOS system name. Probe here too and override the
        # absolute compiler only when the file exists and --version runs.
        working_cc = self._probe_working_cc()
        if working_cc:
            tc.cache_variables["CMAKE_C_COMPILER"] = working_cc
            self.output.info("test_package: pinned CMAKE_C_COMPILER=%s"
                             % working_cc)
        # Target propagation alone proved insufficient (12:51 preflight kept
        # 'pcap.h file not found' after the CMakeLists explicit link). As a
        # propagation-independent fallback, aggregate the real dependency
        # include dirs in Python and append them to CMAKE_C_FLAGS, so the
        # compiler gets -I flags even if a target's INTERFACE_INCLUDE is
        # incomplete on this worker. Pure cpp_info/package_folder read, no
        # shell/pkg-config involved.
        self._inject_dependency_includes(tc)
        tc.generate()
        # Previous round evidence: the cache_variables pin above is NOT
        # enough. The preflight log printed the pin line
        # (pinned .../.harmonybrew/bin/clang) yet CMake still reported
        # CMAKE_C_COMPILER=/data/service/hnp/bin/clang, i.e. the toolchain
        # file's own set() overrides the preset cache entry. So patch the
        # generated conan_toolchain.cmake on disk as the effective route.
        if working_cc:
            self._patch_generated_toolchain(working_cc)

    def _inject_dependency_includes(self, tc):
        flags = []
        seen = set()
        for dep_name in ("libpcap", "libnids"):
            try:
                dep = self.dependencies[dep_name]
            except Exception as exc:
                self.output.info("test_package: no dep %s (%s)"
                                 % (dep_name, exc))
                continue
            candidates = []
            try:
                for inc in (dep.cpp_info.includedirs or []):
                    if os.path.isabs(inc):
                        candidates.append(inc)
                    else:
                        candidates.append(
                            os.path.join(dep.package_folder, inc))
            except Exception as exc:
                self.output.info("test_package: cpp_info read failed %s (%s)"
                                 % (dep_name, exc))
            fallback = os.path.join(dep.package_folder, "include")
            if fallback not in candidates:
                candidates.append(fallback)
            for inc in candidates:
                norm = inc.replace("\\", "/")
                if norm in seen:
                    continue
                seen.add(norm)
                if os.path.isdir(inc):
                    flags.append("-I%s" % norm)
                    self.output.info("test_package: aggregated include %s"
                                     % norm)
                else:
                    self.output.info("test_package: include missing %s"
                                     % norm)
        if flags:
            prev = tc.cache_variables.get("CMAKE_C_FLAGS", "") or ""
            combined = (prev + " " + " ".join(flags)).strip()
            tc.cache_variables["CMAKE_C_FLAGS"] = combined
            self.output.info("test_package: CMAKE_C_FLAGS=%s" % combined)

    def _patch_generated_toolchain(self, working_cc):
        gen = self.generators_folder or ""
        path = os.path.join(gen, "conan_toolchain.cmake")
        try:
            with open(path, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError as exc:
            self.output.warning("test_package: cannot read %s: %s"
                                % (path, exc))
            return
        stale = "/data/service/hnp/bin/clang"
        if stale in content:
            content = content.replace(stale, working_cc)
            try:
                with open(path, "w", encoding="utf-8",
                          errors="surrogateescape") as handle:
                    handle.write(content)
                self.output.info("test_package: patched %s C compiler -> %s"
                                 % (path, working_cc))
            except OSError as exc:
                self.output.warning("test_package: cannot patch %s: %s"
                                    % (path, exc))
        # Same-dir clang++ for the CXX entry when it exists and runs.
        cxx = working_cc.replace("clang", "clang++") if "clang" in working_cc else ""
        if cxx and os.path.isfile(cxx):
            try:
                result = subprocess.run(
                    [cxx, "--version"],
                    capture_output=True, text=True, timeout=30,
                )
            except Exception:
                result = None
            if result is not None and result.returncode == 0:
                try:
                    with open(path, "r", encoding="utf-8",
                              errors="surrogateescape") as handle:
                        content = handle.read()
                    stale_cxx = "/data/service/hnp/bin/clang++"
                    if stale_cxx in content:
                        content = content.replace(stale_cxx, cxx)
                        with open(path, "w", encoding="utf-8",
                                  errors="surrogateescape") as handle:
                            handle.write(content)
                        self.output.info("test_package: patched CXX -> %s" % cxx)
                except OSError as exc:
                    self.output.warning("test_package: cannot patch CXX: %s" % exc)

    def _probe_working_cc(self):
        candidates = []
        try:
            comp = self.conf.get("tools.build:compiler_executables")
            if isinstance(comp, dict) and comp.get("c"):
                candidates.append(comp["c"])
            elif isinstance(comp, str) and comp:
                candidates.append(comp)
        except Exception:
            pass
        for key in ("CC", "HMBS_CC"):
            val = os.environ.get(key)
            if val:
                candidates.append(val)
        for tool in ("clang", "cc", "gcc"):
            try:
                found = shutil.which(tool)
            except Exception:
                found = None
            if found:
                candidates.append(found)
        candidates.append("/data/service/hnp/bin/clang")
        seen = set()
        for cand in candidates:
            if not cand or not isinstance(cand, str):
                continue
            exe = cand.split()[0]
            if not exe or exe in seen:
                continue
            seen.add(exe)
            if "/" in exe and not os.path.isfile(exe):
                continue
            try:
                result = subprocess.run(
                    [exe, "--version"],
                    capture_output=True, text=True, timeout=30,
                )
            except Exception:
                continue
            if result.returncode == 0:
                return exe
        return ""

    def _ensure_writable_tmp(self):
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
                "libnids 1.26 ships no automated test harness: "
                "top-level Makefile.in and src/Makefile.in define no "
                "check/test target, no tests/ or test/ directory, no "
                "CTest/gtest/pytest wiring; samples/ (sniff/printall/"
                "overflows/nids_next/chksum_ctl) are manual programs "
                "requiring root and a live interface; "
                "see test_package/MANIFEST.yml upstream_test_audit"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )

    def _dump_last_test_log(self):
        try:
            candidates = []
            build_folder = getattr(self, "build_folder", "") or ""
            if build_folder and os.path.isdir(build_folder):
                for root, dirs, files in os.walk(build_folder):
                    if "LastTest.log" in files:
                        candidates.append(os.path.join(root, "LastTest.log"))
                    if root.count(os.sep) - build_folder.count(os.sep) > 6:
                        dirs[:] = []
            for log_path in sorted(candidates)[:2]:
                try:
                    with open(log_path, "r", encoding="utf-8",
                              errors="replace") as handle:
                        content = handle.read()
                except OSError:
                    continue
                self.output.info("LastTest.log (%s) tail:" % log_path)
                self.output.info(content[-4000:])
        except Exception:
            pass

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        self._ensure_writable_tmp()
        cmake = CMake(self)
        try:
            cmake.test()
        except Exception as exc:
            self.output.warning("ctest failed: %s" % exc)
            self._dump_last_test_log()
            self._run_consumer_binary(raise_on_failure=False)
            self._emit_upstream_marker()
            raise
        self._run_consumer_binary(raise_on_failure=True)
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_nids")
        self.run(bin_path, env="conanrun")
        self._emit_upstream_marker()
        self.output.info("libnids consumer test_package passed")

    def _run_consumer_binary(self, raise_on_failure):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_nids")
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
