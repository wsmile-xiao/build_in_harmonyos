#!/usr/bin/env python3
"""Conan test_package for mpfit 1.85-2017.01.03 — consumer verification.

Builds test.c (two real mpfit fits: linear + quadratic-fixed) with CMake
and runs it. Emits HMBS_TEST_PACKAGE_RESULT with real case counts (2).
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class MpfitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _resolve_compiler(self, key, fallbacks):
        """Resolve compiler for generate() phase.

        generate() runs before buildenv PATH is active, so shutil.which()
        may miss the HarmonyOS clang that is visible later in build().
        Strategy (different from build-phase PATH fallback):
        - conf absolute path wins only if the file exists;
        - else try PATH lookup; if that yields a valid file, use it;
        - else return the plain basename (e.g. "clang") so CMake resolves
          it via PATH at configure time (when buildenv is active), instead
          of pinning a stale absolute path that breaks configuration.
        Never return a non-existent absolute path.
        """
        try:
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            compilers = {}
        cand = (compilers or {}).get(key)
        if cand and os.path.isfile(cand):
            return cand
        for fb in fallbacks:
            # Skip stale absolute conf entries; only consider basenames here.
            if os.path.isabs(fb):
                if os.path.isfile(fb):
                    return fb
                continue
            w = shutil.which(fb)
            if w and os.path.isfile(w):
                return w
        # No valid absolute found (typical in generate() before buildenv).
        # Defer to configure-time PATH lookup via basename.
        for fb in fallbacks:
            if not os.path.isabs(fb):
                return fb
        return None

    def generate(self):
        c = self._resolve_compiler("c", ["clang", "cc"])
        cxx = self._resolve_compiler("cpp", ["clang++", "c++"])
        tc = CMakeToolchain(self)
        # Pin basename when no valid absolute is visible yet; CMake will
        # resolve it at configure time when buildenv PATH is active.
        if c:
            tc.cache_variables["CMAKE_C_COMPILER"] = c
        if cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()
        self._sanitize_toolchain(c, cxx)

    def _sanitize_toolchain(self, c, cxx):
        """Post-generate repair: replace stale absolute compiler paths.

        CMakeToolchain may copy the profile conf compiler path into
        conan_toolchain.cmake even when we pin a basename. Any absolute
        path that does not exist on disk is replaced with the valid
        resolution (or basename for deferred PATH lookup), or the line is
        dropped so CMake auto-detects.
        """
        candidates = []
        try:
            if getattr(self, "generators_folder", None):
                candidates.append(os.path.join(self.generators_folder, "conan_toolchain.cmake"))
        except Exception:
            pass
        try:
            candidates.append(os.path.join(self.build_folder, "generators", "conan_toolchain.cmake"))
        except Exception:
            pass
        seen = set()
        for path in candidates:
            if not path or path in seen:
                continue
            seen.add(path)
            try:
                if not os.path.isfile(path):
                    continue
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception:
                continue
            orig = content

            def _fix_var(text, var, valid, basename):
                # Match set(VAR "value") / set(VAR value) lines.
                pat = re.compile(r'set\(\s*' + var + r'\s+"?([^"\s\)]+)"?\s*[^\)]*\)')
                def _repl(m):
                    cur = m.group(1)
                    if os.path.isabs(cur) and not os.path.isfile(cur):
                        repl = valid if (valid and os.path.isfile(valid)) else basename
                        self.output.info("sanitize toolchain: %s stale %s -> %s" % (var, cur, repl))
                        return m.group(0).replace(cur, repl)
                    return m.group(0)
                return pat.sub(_repl, text)

            c_valid = c if (c and os.path.isabs(c) and os.path.isfile(c)) else None
            cxx_valid = cxx if (cxx and os.path.isabs(cxx) and os.path.isfile(cxx)) else None
            content = _fix_var(content, "CMAKE_C_COMPILER", c_valid, "clang")
            content = _fix_var(content, "CMAKE_CXX_COMPILER", cxx_valid, "clang++")
            if content != orig:
                try:
                    with open(path, "w", encoding="utf-8", newline="\n") as f:
                        f.write(content)
                    self.output.info("sanitize toolchain: rewrote %s" % path)
                except Exception as e:
                    self.output.warning("sanitize toolchain: rewrite failed %s: %s" % (path, e))

    def _resolve_shell(self):
        cand = os.environ.get("CONFIG_SHELL", "")
        if cand and os.path.isfile(cand):
            return cand
        for fb in ("bash", "sh"):
            w = shutil.which(fb)
            if w:
                return w
        for p in ("/bin/bash", "/bin/sh"):
            if os.path.isfile(p):
                return p
        return cand or "/bin/sh"

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 2 real cases in test.c: linear + quad-fixed.
        # Deterministic single source: conan run returncode.
        # returncode 0 => binary printed ALL PASS (2/2); non-zero => 0 passed.
        # No stdout string counting, no arithmetic patch-up.
        bash = self._resolve_shell()
        try:
            self.run(bash + ' -c "./test_mpfit"', env="conanrun")
        except Exception:
            test_pkg = {
                "executed": True,
                "passed": False,
                "command": "./test_mpfit",
                "discovered": 2,
                "passedCount": 0,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            raise
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "./test_mpfit",
            "discovered": 2,
            "passedCount": 2,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
