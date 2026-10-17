#!/usr/bin/env python3
"""Conan test_package -- librsb 1.3.0.3 consumer tests (R34).

Builds test_librsb against the installed package (CMakeDeps +
CMakeToolchain) and runs it on the native OHOS target. The binary
prints one "CHECK-OK:" line per verified stage (6 total: init, COO
assembly, SpMV, transposed SpMV, beta accumulation, free+exit);
test() counts those lines for the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker (exit-0-alone is not proof).

Upstream suite evidence (examples make tests, 9 steps in the no-Fortran
configuration) is executed inside the main recipe build() which emits
HMBS_UPSTREAM_TEST_RESULT from that real run (top-level `make check` is
upstream `make qtests` brute-force and is intentionally not gated); this
file emits only the
consumer marker, see test_package/MANIFEST.yml.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


CONSUMER_CHECK_COUNT = 6


class LibrsbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        cc, cxx = self._ohos_compiler_fallback()
        bad_cc, bad_cxx = self._ohos_profile_compilers()
        if cc:
            tc.cache_variables["CMAKE_C_COMPILER"] = cc
        if cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx
        tc.generate()
        self._patch_test_toolchain_compiler(cc, cxx, bad_cc, bad_cxx)

    def _ohos_profile_compilers(self):
        try:
            conf = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            conf = {}
        bad_cc = conf.get("c", "") if isinstance(conf, dict) else ""
        bad_cxx = conf.get("cpp", "") if isinstance(conf, dict) else ""
        return bad_cc or "", bad_cxx or ""

    def _patch_test_toolchain_compiler(self, cc, cxx, bad_cc, bad_cxx):
        if not cc and not cxx:
            return
        mapping = {}
        if bad_cc and cc and bad_cc != cc:
            mapping[bad_cc] = cc
        if bad_cxx and cxx and bad_cxx != cxx:
            mapping[bad_cxx] = cxx
        for generic_bad, good in (("/data/service/hnp/bin/clang", cc),
                                  ("/data/service/hnp/bin/clang++", cxx)):
            if good and generic_bad not in mapping and generic_bad != good:
                mapping[generic_bad] = good
        if cc:
            os.environ["CC"] = cc
        if cxx:
            os.environ["CXX"] = cxx
        if not mapping:
            self.output.info("OHOS test toolchain patch: nothing to map")
            return
        folders = []
        for folder in (getattr(self, "generators_folder", None),
                       getattr(self, "build_folder", None)):
            if folder and folder not in folders:
                try:
                    folders.append(str(folder))
                except Exception:
                    continue
        target_names = ("conan_toolchain.cmake", "CMakePresets.json",
                        "CMakeUserPresets.json")
        scanned, patched = [], []
        for folder in folders:
            if not folder or not os.path.isdir(folder):
                continue
            for dirpath, _dirnames, filenames in os.walk(folder):
                for name in filenames:
                    if name not in target_names:
                        continue
                    path = os.path.join(dirpath, name)
                    if path in scanned:
                        continue
                    scanned.append(path)
                    try:
                        with open(path, encoding="utf-8",
                                  errors="surrogateescape") as handle:
                            content = handle.read()
                    except OSError:
                        continue
                    orig = content
                    for bad, good in mapping.items():
                        if bad and good and bad in content:
                            content = content.replace(bad, good)
                    if content != orig:
                        try:
                            with open(path, "w", encoding="utf-8",
                                      errors="surrogateescape") as handle:
                                handle.write(content)
                            patched.append(path)
                        except OSError:
                            continue
        self.output.info(
            "OHOS test toolchain patch: scanned %d file(s), patched %d %s"
            % (len(scanned), len(patched), mapping))
        for path in scanned:
            self.output.info("OHOS test toolchain seen: %s" % path)
        for path in patched:
            self.output.info("OHOS test toolchain patched: %s" % path)
        if not scanned:
            self.output.warning(
                "OHOS test toolchain patch: no toolchain/preset file found "
                "under %s" % (folders,))

    def _ohos_compiler_fallback(self, quiet=False):
        try:
            conf = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            conf = {}
        conf_cc = conf.get("c", "") if isinstance(conf, dict) else ""
        conf_cxx = conf.get("cpp", "") if isinstance(conf, dict) else ""
        if conf_cc and os.path.isfile(conf_cc):
            if not quiet:
                self.output.info(
                    "OHOS test compiler: profile CC present (%s), no override"
                    % conf_cc)
            return "", ""
        cc, cxx = "", ""
        for var in ("CC", "CLANG", "HMBS_CC"):
            val = os.environ.get(var, "")
            if val and os.path.isfile(val):
                cc = val
                break
        if not cc:
            for name in ("clang", "cc", "gcc",
                         "aarch64-unknown-linux-ohos-clang"):
                hit = shutil.which(name)
                if hit and os.path.isfile(hit):
                    cc = hit
                    break
        if not cxx:
            if cc:
                sib = os.path.join(os.path.dirname(cc), "clang++")
                if os.path.isfile(sib):
                    cxx = sib
            if not cxx:
                for var in ("CXX", "CLANGXX", "HMBS_CXX"):
                    val = os.environ.get(var, "")
                    if val and os.path.isfile(val):
                        cxx = val
                        break
            if not cxx:
                for name in ("clang++", "c++", "g++"):
                    hit = shutil.which(name)
                    if hit and os.path.isfile(hit):
                        cxx = hit
                        break
        if not cc:
            self.output.warning(
                "OHOS test compiler: no fallback found (profile %r absent); "
                "leaving toolchain default" % (conf_cc,))
            return "", ""
        if not quiet:
            self.output.info(
                "OHOS test compiler fallback: CC=%s CXX=%s (profile %r absent)"
                % (cc, cxx, conf_cc))
        return cc, cxx

    def build(self):
        cc, cxx = self._ohos_compiler_fallback(quiet=True)
        cmake = CMake(self)
        variables = {}
        if cc:
            variables["CMAKE_C_COMPILER"] = cc
        if cxx:
            variables["CMAKE_CXX_COMPILER"] = cxx
        if variables:
            cmake.configure(variables=variables)
        else:
            cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("librsb target consumers are not runnable")
        binary = self._consumer_binary("test_librsb")
        proc = subprocess.run(
            [binary],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        output = proc.stdout or ""
        self.output.info(output[-2000:])
        passed_count = output.count("CHECK-OK:")
        ok = (proc.returncode == 0 and passed_count == CONSUMER_CHECK_COUNT)
        self.run(binary, env="conanrun")
        tp_marker = {
            "executed": True,
            "passed": ok,
            "command": "test_librsb (rsb_lib_init/alloc/spmv/free/exit)",
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": passed_count,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker)
        )
        if not ok:
            raise ConanException(
                "consumer test failed: ok=%s/%s rc=%s"
                % (passed_count, CONSUMER_CHECK_COUNT, proc.returncode)
            )
        self.output.info("librsb consumer test_package passed")

    def _consumer_binary(self, name):
        binary = os.path.join(self.cpp.build.bindir, name)
        if not os.path.isfile(binary):
            raise ConanException("test binary missing: %s" % binary)
        return binary
