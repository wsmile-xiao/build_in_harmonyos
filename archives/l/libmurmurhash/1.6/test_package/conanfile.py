#!/usr/bin/env python3

import json
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


def _probe_compiler(conanfile, kind):
    try:
        conf = conanfile.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
    except Exception:
        conf = {}
    home = os.path.expanduser("~")
    if kind == "c":
        raw = [shutil.which("clang"), shutil.which("cc"),
               shutil.which("aarch64-linux-ohos-clang"),
               os.path.join(home, "usr", "local", "bin", "clang"),
               "/storage/Users/currentUser/usr/local/bin/clang",
               os.environ.get("CC"),
               conf.get("c"),
               "/data/service/hnp/bin/clang",
               shutil.which("gcc"), "clang", "cc"]
        code = "int probe_main(void){return 0;}\n"
    else:
        raw = [shutil.which("clang++"), shutil.which("c++"),
               shutil.which("aarch64-linux-ohos-clang++"),
               os.path.join(home, "usr", "local", "bin", "clang++"),
               "/storage/Users/currentUser/usr/local/bin/clang++",
               os.environ.get("CXX"),
               conf.get("cpp"),
               "/data/service/hnp/bin/clang++",
               shutil.which("g++"), "clang++", "c++"]
        code = "int probe_main(){return 0;}\n"
    seen = set()
    cands = [c for c in raw if c and not (c in seen or seen.add(c))]
    tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
           or os.environ.get("TEMP") or tempfile.gettempdir())
    try:
        os.makedirs(tmp, exist_ok=True)
    except Exception:
        pass
    src = os.path.join(tmp, f"hmbs_tp_{kind}_{os.getpid()}.c")
    try:
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
    except Exception:
        return cands[0] if cands else "clang"
    try:
        for cand in cands:
            obj = src + ".o"
            try:
                proc = subprocess.run([cand, src, "-c", "-o", obj],
                                      capture_output=True, timeout=120)
            except Exception:
                continue
            if proc.returncode == 0 and os.path.isfile(obj):
                try:
                    os.remove(obj)
                except Exception:
                    pass
                return cand
        raise ConanInvalidConfiguration(
            f"no working compiler found in test_package (tried {cands})")
    finally:
        for p in (src, src + ".o"):
            try:
                if p and os.path.isfile(p):
                    os.remove(p)
            except Exception:
                pass


def _patch_generated_toolchain(conanfile, good_c, good_cxx):
    try:
        conf = conanfile.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
    except Exception:
        conf = {}
    stale = [p for p in (conf.get("c"), conf.get("cpp"),
                         "/data/service/hnp/bin/clang",
                         "/data/service/hnp/bin/clang++") if p]
    stale = [p for p in dict.fromkeys(stale)
             if not (os.path.isfile(p) and os.access(p, os.X_OK))]
    if not stale:
        return
    roots = []
    try:
        gf = getattr(conanfile, "generators_folder", None)
        if gf:
            roots.append(gf)
    except Exception:
        pass
    try:
        if getattr(conanfile, "build_folder", None):
            roots.append(conanfile.build_folder)
    except Exception:
        pass
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            if "conan_toolchain.cmake" not in filenames:
                continue
            tc_path = os.path.join(dirpath, "conan_toolchain.cmake")
            try:
                with open(tc_path, "r", encoding="utf-8", errors="strict") as f:
                    text = f.read()
            except Exception:
                continue
            orig = text
            for bad in stale:
                if bad in text:
                    good = good_cxx if bad.endswith("++") else good_c
                    text = text.replace(bad, good)
            if text != orig:
                try:
                    with open(tc_path, "w", encoding="utf-8") as f:
                        f.write(text)
                except Exception:
                    pass


class LibmurmurhashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # cache_variables override proven ineffective (see main recipe);
        # generate first, then patch the emitted toolchain file.
        tc = CMakeToolchain(self)
        tc.generate()
        good_c = _probe_compiler(self, "c")
        good_cxx = _probe_compiler(self, "cpp")
        _patch_generated_toolchain(self, good_c, good_cxx)
        try:
            os.environ["CC"] = good_c
            os.environ["CXX"] = good_cxx
        except Exception:
            pass
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_libmurmurhash")
            self.run(bin_path, env="conanrun")
            # test.c holds 9 ordered assertions (return codes 1..9); exit 0
            # means all of them passed, and stdout carries the smoke marker.
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": "test_libmurmurhash",
                "discovered": 9,
                "passedCount": 9,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        # Re-emit the upstream result persisted by the main recipe so cache-hit
        # runs (build() skipped) still carry evidence.
        emitted = False
        try:
            dep = self.dependencies[self.tested_reference_str]
            for cand in (
                os.path.join(dep.package_folder, "res", "upstream_test_result.json"),
                os.path.join(dep.package_folder, "upstream_test_result.json"),
            ):
                if os.path.isfile(cand):
                    with open(cand, "r", encoding="utf-8") as f:
                        up = json.load(f)
                    self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(up, ensure_ascii=False))
                    emitted = True
                    break
        except Exception as e:
            self.output.warning(f"upstream re-emit failed: {e}")
        if not emitted:
            self.output.warning("upstream_test_result.json not found in package")
