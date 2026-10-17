#!/usr/bin/env python3
"""Conan test_package for libapk 3.0.6 - consumer API test.

Builds test_apk.c against the packaged libapk (apk::apk) and runs
four real API assertions (version validate/compare/match + blob).
Parses CASE PASS lines for HMBS_TEST_PACKAGE_RESULT, then re-emits
the upstream evidence persisted by the recipe build.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibapkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        self._ensure_writable_tmp("test-generate")
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Force the verified compilers so cmake's compiler check does not
        # use a stale locked absolute path (libsz experience, adapted).
        verified = self._verified_compilers()
        if verified.get("c"):
            tc.cache_variables["CMAKE_C_COMPILER"] = verified["c"]
        if verified.get("cpp"):
            tc.cache_variables["CMAKE_CXX_COMPILER"] = verified["cpp"]
        tc.generate()
        CMakeDeps(self).generate()
        self._rewrite_toolchain_compilers(verified)

    def _ensure_writable_tmp(self, label):
        cands = []
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val:
                cands.append(val)
        for base in (getattr(self, "build_folder", None),
                     getattr(self, "source_folder", None)):
            if base:
                cands.append(os.path.join(base, "hmbs-tmp"))
        for cand in cands:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_test")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("ok")
                os.remove(probe)
                for key in ("TMPDIR", "TMP", "TEMP"):
                    os.environ[key] = cand
                return cand
            except OSError:
                continue
        self.output.warn("writable tmp not found (%s), keep env" % label)
        return os.environ.get("TMPDIR", "")

    def _verified_compilers(self):
        # Probe candidates with --version; prefer PATH-resolved, fall back
        # to the configured absolute path.
        out = {}
        conf = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict) or {}
        for lang, fallback in (("c", "clang"), ("cpp", "clang++")):
            configured = conf.get(lang) or ""
            cands = []
            found = shutil.which(fallback)
            if found:
                cands.append(found)
            if configured and configured not in cands:
                cands.append(configured)
            chosen = ""
            for cand in cands:
                try:
                    proc = subprocess.run([cand, "--version"],
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT,
                                          timeout=30)
                    if proc.returncode == 0:
                        chosen = cand
                        break
                except OSError:
                    continue
            out[lang] = chosen or (cands[0] if cands else fallback)
        return out

    def _rewrite_toolchain_compilers(self, verified):
        # CMakeToolchain only provides the toolchain file, not the cmake
        # binary; rewrite locked compiler entries to the verified paths.
        gf = getattr(self, "generators_folder", None)
        if not gf or not os.path.isdir(gf):
            return
        for fn in os.listdir(gf):
            if fn.startswith("conan_toolchain") and fn.endswith(".cmake"):
                path = os.path.join(gf, fn)
                try:
                    with open(path, "r", encoding="utf-8",
                              errors="replace") as f:
                        content = f.read()
                except OSError:
                    continue
                orig = content
                for lang, var in (("c", "CMAKE_C_COMPILER"),
                                  ("cpp", "CMAKE_CXX_COMPILER")):
                    target = verified.get(lang)
                    if not target:
                        continue
                    lines = content.splitlines(keepends=True)
                    replaced = False
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if stripped.startswith("set(%s " % var):
                            lines[i] = 'set(%s "%s")\n' % (var, target)
                            replaced = True
                    content = "".join(lines)
                    if not replaced:
                        content += 'set(%s "%s")\n' % (var, target)
                if content != orig:
                    try:
                        with open(path, "w", encoding="utf-8",
                                  newline="\n") as f:
                            f.write(content)
                    except OSError:
                        pass

    def build(self):
        self._ensure_writable_tmp("test-build")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._ensure_writable_tmp("test-run")
        if not can_run(self):
            self.output.info("cross-building: skip runtime test")
            return
        binary = os.path.join(self.cpp.build.bindirs[0], "test_apk")
        log_path = os.path.join(self.build_folder, "test_apk.log")
        try:
            self.run(f'"{binary}" > "{log_path}" 2>&1', env="conanrun")
        except ConanException:
            pass
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        self.output.info("test output:\n" + out)
        discovered = 4
        passed_count = out.count("CASE PASS")
        marker = {
            "executed": True,
            "passed": discovered > 0 and passed_count == discovered,
            "command": "./test_apk (libapk version/blob consumer checks)",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        self._emit_upstream_result()
        if not marker["passed"]:
            raise ConanException(f"test_package failed: {passed_count}/{discovered} cases passed")

    def _emit_upstream_result(self):
        dep = self.dependencies["libapk"]
        path = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(path):
            raise ConanException("upstream_test_result.json not found in package")
        with open(path, "r", encoding="utf-8") as f:
            result = json.load(f)
        ok_shape = (
            isinstance(result, dict)
            and result.get("status") == "passed"
            and int(result.get("discovered", 0)) > 0
            and int(result.get("executed", 0)) == int(result.get("discovered", 0))
            and int(result.get("passed", 0)) == int(result.get("discovered", 0))
            and int(result.get("failed", 0)) == 0
            and int(result.get("skipped", 0)) == 0
        )
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        if not ok_shape:
            raise ConanException(f"upstream test evidence invalid: {result}")
