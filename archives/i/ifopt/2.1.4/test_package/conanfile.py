#!/usr/bin/env python3
"""Consumer test for ifopt/2.1.4 (links the installed ifopt_core)."""

import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class IfoptTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        candidates = []
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR",
                    "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            val = os.getenv(key)
            if val and val not in candidates:
                candidates.append(val)
        home = os.path.expanduser("~")
        if home and home != "~":
            home_tmp = os.path.join(home, "tmp")
            if home_tmp not in candidates:
                candidates.append(home_tmp)
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                local_tmp = os.path.join(bf, "hmbs-tmp")
                if local_tmp not in candidates:
                    candidates.append(local_tmp)
        except Exception:
            pass
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w") as f:
                    f.write("ok")
                os.remove(probe)
                os.environ["TMPDIR"] = cand
                os.environ["TMP"] = cand
                os.environ["TEMP"] = cand
                os.environ["GOTMPDIR"] = cand
                return cand
            except Exception:
                continue
        return None

    def generate(self):
        self._ensure_writable_tmp()
        tc = CMakeToolchain(self)
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
        self.output.info("HMBS diag test_package compilers c=%s cxx=%s"
                         % (_c, _cxx))
        tc.generate()
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()
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
                        "HMBS diag fixed test_package toolchain %s" % path)
        except Exception as e:
            self.output.warning("HMBS diag toolchain fix failed: %s" % e)
        try:
            comp_env = Environment()
            if c_old and c and (c_old, c) in pairs:
                comp_env.define("CC", c)
            if cxx_old and cxx and (cxx_old, cxx) in pairs:
                comp_env.define("CXX", cxx)
            comp_env.vars(self, scope="build").save_sh("hmbs_compiler")
        except Exception as e:
            self.output.warning(
                "HMBS diag compiler env export failed: %s" % e)

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _hmbs_emit(self, line):
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass

    def test(self):
        self._ensure_writable_tmp()
        if cross_building(self):
            self.output.info("cross-building: consumer compiled and linked")
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_ifopt")
        self.run(executable, env="conanrun")
        # The consumer binary runs 13 real API checks (exit nonzero on any
        # failure above): 1 genuine test case.
        self._hmbs_emit("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(
            {"executed": True, "passed": True,
             "command": "./test_ifopt",
             "discovered": 1, "passedCount": 1},
            separators=(",", ":")))
        # Re-emit the real upstream result carried in the package res/ so
        # cache-hit runs still provide evidence every round. Accept both
        # full-pass and honest partial-run markers (failed + gaps/reason);
        # only garbage/empty payloads are refused.
        try:
            res = os.path.join(
                self.dependencies["ifopt"].package_folder,
                "res", "hmbs_upstream.json")
            with open(res, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if int(payload.get("discovered", 0)) > 0 and \
                    int(payload.get("executed", 0)) > 0 and \
                    payload.get("status") in ("passed", "failed"):
                self._hmbs_emit("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
                    payload, separators=(",", ":")))
            else:
                self.output.warning(
                    "HMBS diag upstream res invalid: %s" % payload)
        except Exception as e:
            self.output.warning("HMBS diag upstream res missing: %s" % e)
