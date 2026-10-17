#!/usr/bin/env python3
"""Conan test_package -- lodepng 0.0-git20250402.c45ed79 consumer test.

Direct-compiler build (no CMake): links test_lodepng.cpp against the
Conan package liblodepng and runs the resulting binary (5 real
encode/decode assertion groups, R34). The binary itself prints
HMBS_TEST_PACKAGE_RESULT; here we also re-emit the build() persisted
upstream verdict so the marker survives Conan cache hits.

Why no CMake: the ohos-aarch64 profile pins
tools.build:compiler_executables to /data/service/hnp/bin/clang++,
which is inaccessible on some HMBS preflight workers (exit 127 at
CMake compiler check) while PATH-probed tools work. CMakeToolchain
embeds that absolute path unconditionally, so test_package avoids it
entirely and resolves the compiler the same way the main recipe does
(conf value only when isfile + X_OK, else PATH lookup).
"""
import json
import os
import shutil
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class LodepngTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _conf_exe(self, key):
        try:
            exes = self.conf.get("tools.build:compiler_executables", check_type=dict)
        except Exception:
            exes = None
        if isinstance(exes, dict) and exes.get(key):
            return exes[key]
        try:
            value = self.conf.get(
                "tools.build:compiler_executables:%s" % key, None, check_type=str
            )
            if value:
                return value
        except Exception:
            pass
        return None

    @staticmethod
    def _is_usable_exe(path):
        try:
            return os.path.isfile(path) and os.access(path, os.X_OK)
        except Exception:
            return False

    def _resolve_prog(self, key, env_vars, path_names):
        conf_val = self._conf_exe(key)
        if conf_val:
            if os.path.isabs(conf_val):
                if self._is_usable_exe(conf_val):
                    return conf_val
                try:
                    self.output.warning(
                        "conf compiler '%s' not usable, falling back to PATH lookup"
                        % conf_val
                    )
                except Exception:
                    pass
            else:
                resolved = shutil.which(conf_val)
                if resolved:
                    return resolved
        for var in env_vars:
            val = os.environ.get(var, "")
            if not val:
                continue
            if os.path.sep in val:
                if self._is_usable_exe(val) or os.path.isfile(val):
                    return val
            else:
                resolved = shutil.which(val)
                if resolved:
                    return resolved
                return val
        for name in path_names:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                return found
        if conf_val:
            return conf_val
        return path_names[0] if path_names else key

    def _writable_tmpdir(self):
        candidates = []
        fallback = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK", "")
        if fallback and fallback not in ("0", "1") and fallback != "/tmp":
            candidates.append(fallback)
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(var, "")
            if val and val != "/tmp" and val not in candidates:
                candidates.append(val)
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                fd, p = tempfile.mkstemp(dir=cand)
                os.close(fd)
                os.unlink(p)
                return cand
            except Exception:
                continue
        fb = os.path.join(self.build_folder or os.getcwd(), "tmp")
        try:
            os.makedirs(fb, exist_ok=True)
        except OSError:
            pass
        return fb

    def _pin_writable_tmpdir(self):
        tmp = self._writable_tmpdir()
        try:
            os.makedirs(tmp, exist_ok=True)
        except OSError:
            pass
        for k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[k] = tmp
        return tmp

    def _prepend_toolchain_path(self, prog):
        if not prog:
            return
        d = os.path.dirname(prog)
        if not d or not os.path.isdir(d):
            return
        cur = os.environ.get("PATH", "")
        parts = cur.split(os.pathsep) if cur else []
        if d in parts:
            return
        os.environ["PATH"] = d + os.pathsep + cur

    def build(self):
        tmp = self._pin_writable_tmpdir()
        self.output.info("HMBS readonly_tmp: TMPDIR=%s" % tmp)
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        os.environ["SHELL"] = "/bin/sh"
        cxx = self._resolve_prog(
            "cpp", ("CXX", "HMBS_CXX"), ("clang++", "clang", "c++", "cc")
        )
        self._prepend_toolchain_path(cxx)
        self.output.info("lodepng test_package cxx resolved: %s" % cxx)
        dep = self.dependencies["lodepng"]
        include_dir = os.path.join(str(dep.package_folder), "include")
        lib_dir = os.path.join(str(dep.package_folder), "lib")
        src = os.path.join(self.source_folder, "test_lodepng.cpp")
        out = os.path.join(self.build_folder, "test_lodepng")
        self.run(
            '"%s" -O2 -I"%s" "%s" -L"%s" -llodepng -o "%s"'
            % (cxx, include_dir, src, lib_dir, out),
            env="conanbuild",
        )

    def test(self):
        try:
            dep = self.dependencies["lodepng"]
            marker_file = os.path.join(
                str(dep.package_folder), "hmbs_upstream_result.json"
            )
            if os.path.isfile(marker_file):
                with open(marker_file, encoding="utf-8") as fh:
                    data = json.load(fh)
                marker = {
                    k: data.get(k)
                    for k in (
                        "status",
                        "framework",
                        "command",
                        "discovered",
                        "executed",
                        "passed",
                        "failed",
                        "skipped",
                    )
                }
                if "reason" in data:
                    marker["reason"] = data["reason"]
                line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
                print(line, flush=True)
                self.output.info(line)
        except Exception:
            pass
        if not can_run(self):
            self.output.info("cross-building: test binary built but not run on host")
            return
        binary = os.path.join(self.build_folder, "test_lodepng")
        self.run(binary, env="conanrun")
