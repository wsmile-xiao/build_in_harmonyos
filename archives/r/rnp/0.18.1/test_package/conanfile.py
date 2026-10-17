#!/usr/bin/env python3
"""Conan test_package — rnp 0.18.1 (Conan L1 official test)."""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMakeDeps, cmake_layout


class RnpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        # NOTE: no CMakeToolchain (same reason as the main recipe: stock
        # cmake rejects the OHOS HarmonyOS system name; build() uses the
        # SDK ohos.toolchain.cmake + bare cmake instead).

    def _cmake_exe(self):
        try:
            val = self.conf.get("user.hmbs:cmake_path", check_type=str)
            if val and os.path.isfile(val.split()[0].strip("\"'")):
                return val.split()[0].strip("\"'")
        except ConanException:
            pass
        return os.environ.get("HMBS_CMAKE") or "cmake"

    def _ohos_toolchain(self):
        import glob
        try:
            ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain",
                               default=[], check_type=list) or []
        except Exception:
            ut = []
        for cand in list(ut):
            try:
                if cand and os.path.isfile(cand):
                    return cand
            except Exception:
                continue
        patterns = [
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/storage/Users/currentUser/usr/local/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/storage/Users/currentUser/.harmonybrew/Cellar/ohos-sdk/*/native/build/cmake/ohos.toolchain.cmake",
            "/data/service/hnp/ohos-sdk/*/ohos/native/build/cmake/ohos.toolchain.cmake",
        ]
        try:
            home = os.path.expanduser("~")
            if home and home != "~":
                patterns.append(os.path.join(
                    home, ".harmonybrew/Cellar/ohos-sdk/*/native/build/cmake/ohos.toolchain.cmake"))
                patterns.append(os.path.join(
                    home, "usr/local/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        except Exception:
            pass
        for pattern in patterns:
            try:
                found = sorted(glob.glob(pattern))
            except Exception:
                found = []
            if found:
                return found[-1]
        return ""

    def _cmake_generator_arg(self):
        import shutil as _shutil
        cands = []
        try:
            cands.append(os.environ.get("HMBS_NINJA", ""))
        except Exception:
            pass
        try:
            v = self.conf.get("user.hmbs:ninja_path", check_type=str)
            if v:
                cands.append(v)
        except Exception:
            pass
        cands.append("ninja")
        for cand in cands:
            try:
                prog = (cand or "").strip().split()[0].strip("\"'") if cand else ""
            except Exception:
                continue
            if not prog:
                continue
            exe = prog if os.path.isabs(prog) else (_shutil.which(prog) or "")
            if not exe or not (os.path.isfile(exe) and os.access(exe, os.X_OK)):
                continue
            try:
                r = subprocess.run([exe, "--version"], stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, timeout=20)
                if r.returncode == 0:
                    self.output.info("rnp test_package generator: Ninja via {}".format(exe))
                    return '-G "Ninja"'
            except Exception:
                continue
        return ""

    def build(self):
        cmake = self._cmake_exe()
        toolchain = self._ohos_toolchain()
        gen = self._cmake_generator_arg()
        bdir = os.path.join(self.build_folder, "build-ohos")
        try:
            gens = self.generators_folder
        except Exception:
            gens = os.path.join(self.build_folder, "generators")
        self.output.info("rnp test_package generators={} bdir={}".format(gens, bdir))
        try:
            pkg_folder = self.dependencies[self.tested_reference_str.split("/")[0]].package_folder
        except Exception:
            try:
                pkg_folder = self.dependencies["rnp"].package_folder
            except Exception:
                pkg_folder = ""
        prefix_path = gens + (";" + pkg_folder if pkg_folder else "")
        # ohos.toolchain.cmake forces CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY
        # (CACHE FORCE), so CMAKE_PREFIX_PATH alone cannot locate the
        # CMakeDeps configs in the host generators dir: the previous round
        # proved -Drnp_DIR fixes rnp itself, then rnp-config.cmake's own
        # find_dependency(botan3) fails the same way. <dep>_DIR variables
        # bypass FIND_ROOT modes entirely, so pass one per generated config.
        config_dir_defs = ""
        try:
            import glob as _glob
            seen = set()
            for _cfg in _glob.glob(os.path.join(gens, "*-config.cmake")) + \
                       _glob.glob(os.path.join(gens, "*Config.cmake")):
                _base = os.path.basename(_cfg)
                if _base.endswith("-config.cmake"):
                    _stem = _base[: -len("-config.cmake")]
                elif _base.endswith("Config.cmake"):
                    _stem = _base[: -len("Config.cmake")]
                else:
                    continue
                for _var in ({_stem, _stem.lower(), _stem.upper()}):
                    if _var and _var not in seen:
                        seen.add(_var)
                        config_dir_defs += ' -D%s_DIR="%s"' % (_var, gens)
            self.output.info("rnp test_package config _DIRs for={} defs_len={}".format(
                sorted(seen), len(config_dir_defs)))
        except Exception as exc:
            self.output.warning("rnp test_package config scan failed: {}".format(exc))
        defs = [
            '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_PREFIX_PATH="%s"' % prefix_path,
            '-Drnp_DIR="%s"' % gens,
            '-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH',
            '-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=BOTH',
            '-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=BOTH',
        ]
        if config_dir_defs:
            defs.append(config_dir_defs)
        if toolchain:
            defs.insert(0, '-DCMAKE_TOOLCHAIN_FILE="%s"' % toolchain)
            defs.insert(1, '-DOHOS_ARCH=arm64-v8a')
        self.output.info("rnp test_package toolchain={} generator={}".format(toolchain or "<none>", gen or "default"))
        self.run('"%s" %s -B "%s" -S "%s" %s' % (cmake, gen, bdir, self.source_folder,
                                              " ".join(defs)), env="conanbuild")
        self.run('"%s" --build "%s" -j1' % (cmake, bdir), env="conanbuild")
        self._bdir = bdir

    def _test_bdir(self):
        try:
            bdir = getattr(self, "_bdir", "")
        except Exception:
            bdir = ""
        if bdir and os.path.isdir(bdir):
            return bdir
        cand = os.path.join(self.build_folder, "build-ohos")
        return cand if os.path.isdir(cand) else self.build_folder

    def test(self):
        bdir = self._test_bdir()
        ctest = self._resolve_ctest()
        try:
            self.run('"%s" --output-on-failure' % ctest, cwd=bdir,
                     ignore_errors=True)
        except Exception as exc:
            self.output.warning("test_package ctest failed: {}".format(exc))
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        bindir = bdir
        try:
            cand0 = self.cpp.build.bindirs[0]
            if cand0 and os.path.isfile(os.path.join(cand0, "test_rnp")):
                bindir = cand0
        except Exception:
            pass
        if not os.path.isfile(os.path.join(bindir, "test_rnp")):
            for root, _dirs, files in os.walk(bdir):
                if "test_rnp" in files:
                    bindir = root
                    break
        test_bin = os.path.join(bindir, "test_rnp")
        # Run via bash: OHOS /system/bin/sh (mksh) cannot exec ELF directly.
        proc = subprocess.run(
            [bash, "-c", "./test_rnp"],
            capture_output=True, text=True, timeout=300,
            cwd=bindir,
        )
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        self.output.info(output)
        # Falsifiability: binary output must be non-empty and contain checks.
        if not output.strip() or "CHECK " not in output:
            raise ConanException("test_rnp produced no check output")
        passed = len(re.findall(r"^CHECK .*: PASS", output, re.M))
        total = len(re.findall(r"^CHECK ", output, re.M))
        ok = proc.returncode == 0 and passed == total and total == 3
        if not ok:
            raise ConanException(
                "test_rnp failed: rc={} passed={}/{}".format(proc.returncode, passed, total)
            )
        marker = {
            "executed": True,
            "passed": True,
            "command": "./test_rnp",
            "discovered": total,
            "passedCount": passed,
        }
        print("HMBS_TEST_PACKAGE_RESULT={}".format(
            json.dumps(marker, ensure_ascii=False)))

    def _resolve_ctest(self):
        """Resolve a runnable ctest; never return a non-existent absolute path.

        Preflight 2026-09-24 proved the old sibling derivation
        (cmake_path [.../bin/cmake] -> [.../bin/ctest]) emits a literal
        RUN that /bin/sh reports `inaccessible or not found`: HMBS only
        probes cmake/make/ninja/python3, and its cmake dir ships no ctest
        sibling. Prefer PATH, accept the sibling only when it exists.
        """
        import shutil as _shutil

        def _ok(p):
            try:
                prog = (p or "").strip().split()[0].strip("\"'") if p else ""
            except Exception:
                return ""
            if not prog:
                return ""
            if os.path.isabs(prog):
                try:
                    if os.path.isfile(prog) and os.access(prog, os.X_OK):
                        return prog
                except Exception:
                    return ""
                return ""
            try:
                w = _shutil.which(prog)
                return w or ""
            except Exception:
                return ""

        try:
            w = _shutil.which("ctest") or ""
        except Exception:
            w = ""
        hit = _ok(w)
        if hit:
            return hit
        for src in (self._cmake_exe(),):
            try:
                prog = (src or "").strip().split()[0].strip("\"'") if src else ""
            except Exception:
                prog = ""
            if prog and prog.endswith("cmake"):
                sib = prog[: -len("cmake")] + "ctest"
                hit = _ok(sib)
                if hit:
                    return hit
                self.output.warning(
                    "rnp test_package ctest sibling absent (cmake={} sibling={})".format(
                        prog, sib))
        try:
            conf_cmake = self.conf.get("user.hmbs:cmake_path", check_type=str) or ""
        except Exception:
            conf_cmake = ""
        try:
            prog2 = conf_cmake.strip().split()[0].strip("\"'") if conf_cmake else ""
        except Exception:
            prog2 = ""
        if prog2 and prog2.endswith("cmake"):
            hit = _ok(prog2[: -len("cmake")] + "ctest")
            if hit:
                return hit
        for cand in ("/data/service/hnp/bin/ctest",
                     "/usr/local/bin/ctest",
                     "/storage/Users/currentUser/usr/local/bin/ctest"):
            hit = _ok(cand)
            if hit:
                return hit
        return "ctest"

    def _resolve_tool(self, conf_key, env_var, fallback):
        try:
            val = self.conf.get(conf_key, check_type=str)
            if val:
                return val
        except ConanException:
            pass
        return os.environ.get(env_var) or fallback
