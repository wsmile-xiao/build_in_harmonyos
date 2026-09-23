#!/usr/bin/env python3
"""Conan test_package for libics 1.7.0 — Conan L1 official test.

Builds test.c against the packaged library (CMakeDeps +
CMakeToolchain), runs it on the native OHOS target and counts the
per-check "CHECK-OK:" lines for the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker (exit-0-alone is not proof: 5 CHECK-OK lines
are required for a pass).
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


CONSUMER_CHECK_COUNT = 5


class LibicsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # Same E092 minimal alias as the main recipe, in lockstep:
            # plain tc.variables Linux only (libwmime-r16 precedent).
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            self._guard_ohos_compiler(tc)
        tc.generate()

    def _guard_ohos_compiler(self, tc):
        """Same conf-compiler guard as the main recipe (ayatana-ido)."""
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default=None)
        except Exception:
            exes = None
        conf_c = conf_cxx = None
        if isinstance(exes, dict):
            conf_c = exes.get("c")
            conf_cxx = (exes.get("cpp") or exes.get("cxx")
                        or exes.get("c"))
        for key, conf_val, bare in (
                ("CMAKE_C_COMPILER", conf_c, "clang"),
                ("CMAKE_CXX_COMPILER", conf_cxx, "clang++")):
            if conf_val and (os.path.sep in str(conf_val)
                             or "/" in str(conf_val)):
                try:
                    ok = (os.path.isfile(str(conf_val))
                          and os.access(str(conf_val), os.X_OK))
                except Exception:
                    ok = False
                if not ok:
                    self.output.warning(
                        "conf compiler '%s' unusable; falling back to PATH"
                        % conf_val)
                    which = shutil.which(bare)
                    if which:
                        tc.variables[key] = which

    def build(self):
        tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if not (tmp and os.path.isdir(tmp)):
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
            os.environ["TMPDIR"] = tmp
            os.environ["TMP"] = tmp
            os.environ["TEMP"] = tmp
        self._ensure_lld_runnable()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _ensure_lld_runnable(self):
        """Prepend SDK llvm/lib to LD_LIBRARY_PATH so lld can start (E266).

        test_package links the test_libics executable, which needs the
        same working lld as the main recipe's 20 upstream test binaries
        (julius-1.8.0 merged precedent). Derived dynamically via
        clang -print-resource-dir; graceful no-op when unavailable.
        """
        candidates = []
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default=None)
        except Exception:
            exes = None
        if isinstance(exes, dict):
            for key in ("c", "cpp", "cxx"):
                val = exes.get(key)
                if val:
                    candidates.append(str(val))
        which_clang = shutil.which("clang")
        if which_clang:
            candidates.append(which_clang)
        for cc in candidates:
            try:
                out = subprocess.check_output(
                    [cc, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL, text=True).strip()
            except Exception:
                continue
            lib = os.path.dirname(os.path.dirname(out))
            if lib and os.path.isfile(
                    os.path.join(lib, "libxml2.so.16")):
                old = os.environ.get("LD_LIBRARY_PATH", "")
                if old.split(":")[0] != lib:
                    os.environ["LD_LIBRARY_PATH"] = (
                        lib + (":" + old if old else ""))
                    self.output.info(
                        "lld compat: prepended SDK llvm/lib: %s" % lib)
                return
        self.output.info("lld compat: no SDK llvm/lib found, skipping")

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile/link test completed")
            return
        tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if not (tmp and os.path.isdir(tmp)):
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
            os.environ["TMPDIR"] = tmp
            os.environ["TMP"] = tmp
            os.environ["TEMP"] = tmp
        try:
            cmake = CMake(self)
            cmake.test()
        except Exception as exc:
            self.output.warning("ctest failed: %s" % exc)
            raise
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libics")
        if not os.path.isfile(bin_path):
            raise ConanException("test binary missing: %s" % bin_path)
        proc = subprocess.run(
            [bin_path],
            cwd=self.build_folder,
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
        msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
        if not marker["passed"]:
            raise ConanException(
                "consumer test failed: rc=%s ok=%s/%s"
                % (proc.returncode, ok_count, CONSUMER_CHECK_COUNT)
            )
        self.run(bin_path, env="conanrun")
        self._reemit_upstream_marker()
        self.output.info("libics consumer test_package passed")

    def _reemit_upstream_marker(self):
        # Cache-hit re-emit: when Conan reuses the main-package binary,
        # build() is skipped and its HMBS_UPSTREAM_TEST_RESULT never
        # prints. Re-print the persisted real result (written by build()
        # into package res/hmbs_upstream.json) every run so the evidence
        # gate sees it. No test is redefined here.
        try:
            pkg_name = self.tested_reference_str.split("/")[0]
            dep = self.dependencies[pkg_name]
            package_folder = getattr(dep, "package_folder", None)
            if package_folder:
                candidate = os.path.join(str(package_folder), "res", "hmbs_upstream.json")
                if os.path.isfile(candidate):
                    with open(candidate, "r", encoding="utf-8") as handle:
                        upstream = json.load(handle)
                    if isinstance(upstream, dict) and upstream.get("discovered"):
                        umsg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                            upstream, ensure_ascii=False)
                        print(umsg, flush=True)
                        self.output.info(umsg)
                        return
            self.output.warning(
                "persisted hmbs_upstream.json missing; "
                "upstream evidence only available on fresh build")
        except Exception as exc:
            self.output.warning("upstream re-emit skipped: %s" % exc)
