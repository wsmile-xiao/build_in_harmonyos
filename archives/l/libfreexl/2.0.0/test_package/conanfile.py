#!/usr/bin/env python3
"""Consumer test for libfreexl 2.0.0."""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibfreexlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Forward HMBS writable TMPDIR so compiler temp files never use
        # read-only /tmp (E002).
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val:
                try:
                    os.makedirs(val, exist_ok=True)
                except Exception:
                    pass
                self.buildenv_info.define(key, val)
                self.runenv_info.define(key, val)

    def build(self):
        # Existence-checked compiler (crunch-dxtc experience 1, adapted):
        # the profile pins /data/service/hnp/bin/clang(++) which is ENOENT
        # in the preflight sandbox. Probe for a driver that answers
        # --version, bake it into the CMake configure command line and
        # scrub the stale string from conan_toolchain.cmake (dual
        # override). Same-value path replacement only; test scope
        # unchanged.
        cc = self._resolve_compiler("c")
        cxx = self._resolve_compiler("cpp")
        if cc or cxx:
            self._scrub_toolchain(cc, cxx)
        for var, val in (("CC", cc), ("CXX", cxx)):
            if val:
                os.environ[var] = val
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

    def _probe_compiler(self, resolved):
        try:
            proc = subprocess.run([resolved, "--version"],
                                  capture_output=True, text=True,
                                  timeout=60, env=dict(os.environ))
        except (OSError, subprocess.SubprocessError):
            return False
        return proc.returncode == 0

    def _resolve_compiler(self, kind):
        try:
            comp = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            comp = {}
        cands = []
        if kind == "c":
            for v in (comp.get("c", ""), comp.get("cc", ""),
                      os.environ.get("CC", "")):
                if v:
                    cands.append(v)
        else:
            for v in (comp.get("cpp", ""), comp.get("cxx", ""),
                      comp.get("c++", ""), os.environ.get("CXX", ""),
                      os.environ.get("CC", "")):
                if v:
                    cands.append(v)
        import glob as _glob
        for pat in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang++",
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang",
                    "/data/service/hnp/*/llvm/bin/clang++",
                    "/data/service/hnp/*/llvm/bin/clang"):
            try:
                cands.extend(sorted(_glob.glob(pat)))
            except Exception:
                continue
        for fb in (["clang", "cc", "gcc"] if kind == "c"
                   else ["clang++", "clang", "c++", "g++"]):
            hit = shutil.which(fb)
            cands.append(hit or fb)
        seen = set()
        for cand in cands:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            resolved = cand
            if not os.path.isabs(cand) or not os.path.isfile(cand):
                hit = shutil.which(cand)
                if hit:
                    resolved = hit
                elif not os.path.isfile(resolved):
                    continue
            if not os.path.isfile(resolved):
                continue
            if self._probe_compiler(resolved):
                if resolved != cand:
                    self.output.info("test_package resolved compiler %s -> %s" % (cand, resolved))
                return resolved
        return ""

    def _scrub_toolchain(self, cc, cxx):
        try:
            comp = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            comp = {}
        stale = sorted(set([str(v) for v in comp.values() if v]
                             + ["/data/service/hnp/bin/clang++",
                                "/data/service/hnp/bin/clang"]),
                       key=len, reverse=True)
        if not (cc or cxx):
            return
        for root, _dirs, files in os.walk(self.build_folder):
            if "conan_toolchain.cmake" not in files:
                continue
            path = os.path.join(root, "conan_toolchain.cmake")
            try:
                with open(path, "r", encoding="utf-8",
                          errors="replace") as handle:
                    content = handle.read()
            except OSError:
                continue
            orig = content
            for bad in stale:
                if not bad or bad not in content:
                    continue
                if bad.endswith("++"):
                    repl = cxx or cc
                else:
                    repl = cc or cxx
                if repl and repl != bad:
                    content = content.replace(bad, repl)
            if content != orig:
                try:
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(content)
                except OSError:
                    continue
                self.output.info("test_package scrubbed stale compiler -> %s / %s" % (cc, cxx))

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: consumer executable compiled and linked")
            return
        tmp_base = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, "tmp")
        )
        try:
            os.makedirs(tmp_base, exist_ok=True)
        except Exception:
            pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp_base
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_libfreexl")
        self.run(test_binary, env="conanrun")
        # Re-emit upstream verdict persisted by the main recipe so the
        # HMBS gate has evidence even on binary-cache hits.
        try:
            pkg_folder = self.dependencies["libfreexl"].package_folder
            result_path = os.path.join(str(pkg_folder), "res", "upstream_test_result.json")
            if os.path.isfile(result_path):
                with open(result_path, encoding="utf-8") as handle:
                    data = json.load(handle)
                marker = "HMBS_UPSTREAM_TEST_RESULT={}".format(json.dumps(data))
                self.output.info(marker)
                print(marker, flush=True)
        except Exception as exc:
            self.output.warning("could not re-emit upstream result: {}".format(exc))
        result = {
            "executed": True,
            "passed": True,
            "command": "./test_libfreexl",
            "discovered": 1,
            "passedCount": 1,
        }
        marker = "HMBS_TEST_PACKAGE_RESULT={}".format(json.dumps(result))
        self.output.info(marker)
        print(marker, flush=True)
