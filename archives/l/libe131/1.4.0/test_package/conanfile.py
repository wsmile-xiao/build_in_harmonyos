#!/usr/bin/env python3
"""Conan test_package for libe131 1.4.0."""

import glob
import os
import re
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Libe131TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        if str(self.settings.os) == "OHOS":
            self._ensure_writable_tmpdir()
            self._prepend_ohos_tool_paths()
            self._patch_cmake_toolchain_compilers()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            test_bin = os.path.join(self.cpp.build.bindir, "test_libe131")
            self.run(test_bin, env="conanrun")

    def _ensure_writable_tmpdir(self):
        """Point TMPDIR/TMP/TEMP at a probed writable dir (OHOS /tmp is erofs)."""
        candidates = []
        fallback_var = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK", "")
        if fallback_var and fallback_var not in ("0", "1"):
            candidates.append(fallback_var)
        for var in ("HMBS_TMPDIR",):
            val = os.environ.get(var, "")
            if val and val != "/tmp" and val not in candidates:
                candidates.append(val)
        for var in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(var, "")
            if val and val != "/tmp" and val not in candidates:
                candidates.append(val)
        chosen = ""
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_probe")
                with open(probe, "w") as handle:
                    handle.write("probe")
                try:
                    os.remove(probe)
                except OSError:
                    pass
                chosen = cand
                break
            except OSError:
                continue
        if not chosen:
            chosen = os.path.join(self.build_folder or os.getcwd(), ".conan_tmp")
            try:
                os.makedirs(chosen, exist_ok=True)
            except OSError:
                pass
        for key in ("TMPDIR", "TMP", "TEMP", "TMP_DIR"):
            os.environ[key] = chosen
        self.output.info("OHOS test_package tmpdir=%s" % chosen)

    def _prepend_ohos_tool_paths(self):
        existing = os.environ.get("PATH", "")
        parts = existing.split(os.pathsep) if existing else []
        for path in reversed(self._ohos_tool_paths()):
            if path not in parts:
                existing = path + (os.pathsep + existing if existing else "")
                parts.insert(0, path)
        os.environ["PATH"] = existing

    def _ohos_tool_paths(self):
        cands = [
            "/data/service/hnp/bin",
            os.path.join(os.path.expanduser("~"), ".harmonybrew", "bin"),
            os.path.join(os.path.expanduser("~"), "usr", "local", "bin"),
            "/bin",
            "/usr/bin",
        ]
        return [p for p in cands if p and os.path.isdir(p)]

    def _fallback_compiler(self, compiler_key, fallback_name):
        """Return an existing compiler when the profile path is missing, else None."""
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            compilers = {}
        configured = compilers.get(compiler_key, "")
        if configured:
            first = str(configured).split()[0].strip("\"'")
            if os.path.isfile(first) and os.access(first, os.X_OK):
                return None
        for var in ("CC", "CXX", "HMBS_CC", "HMBS_CXX", "CLANG", "CLANGXX"):
            val = os.environ.get(var, "")
            if val and os.path.isfile(val) and os.access(val, os.X_OK):
                if compiler_key == "cpp" and os.path.basename(val) == "clang":
                    sib = os.path.join(os.path.dirname(val), "clang++")
                    if os.path.isfile(sib):
                        return sib
                if compiler_key == "c" and os.path.basename(val) in ("clang++", "c++", "g++"):
                    continue
                return val
        hit = shutil.which(fallback_name)
        if hit and os.path.isfile(hit) and os.access(hit, os.X_OK):
            return hit
        # Well-known OHOS/SDK locations (existence-checked, never blindly used).
        patterns = (
            os.path.join(os.path.expanduser("~"), ".harmonybrew", "bin", fallback_name),
            "/data/service/hnp/bin/" + fallback_name,
            "/storage/Users/currentUser/usr/local/bin/" + fallback_name,
        )
        for pat in patterns:
            if os.path.isfile(pat) and os.access(pat, os.X_OK):
                return pat
        for pat in (
            "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/" + fallback_name,
            "/data/service/hnp/*/ohos/native/llvm/bin/" + fallback_name,
            "/data/service/hnp/*/llvm/bin/" + fallback_name,
            "/opt/ohos-sdk*/ohos/native/llvm/bin/" + fallback_name,
        ):
            try:
                hits = sorted(glob.glob(pat))
            except Exception:
                continue
            for cand in hits:
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
        return None

    def _patch_cmake_toolchain_compilers(self):
        """Replace stale profile compiler paths in conan_toolchain.cmake.

        Setting cache_variables alone is not enough: the generated toolchain
        file's set(CMAKE_C_COMPILER "<stale>") overrides -D on the command
        line (crunch-dxtc precedent), so the same discovered value must be
        patched into the file. Only replaces when the configured path is
        actually missing; keeps flags/sysroot untouched.
        """
        folder = self.generators_folder
        if not folder or not os.path.isdir(folder):
            return
        replacements = {
            "C": self._fallback_compiler("c", "clang"),
            "CXX": self._fallback_compiler("cpp", "clang++"),
        }
        if not any(replacements.values()):
            self.output.info("OHOS test_package: profile compilers present, no patch")
            return
        path = os.path.join(folder, "conan_toolchain.cmake")
        if not os.path.isfile(path):
            return
        try:
            with open(path, encoding="utf-8", errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            return
        orig = content
        for lang, replacement in replacements.items():
            if not replacement:
                continue
            content, n = re.subn(
                r'(set\s*\(\s*CMAKE_%s_COMPILER\s+)"[^"]+"' % lang,
                r'\1"%s"' % replacement,
                content,
            )
            if n:
                self.output.info(
                    "OHOS patch applied (test_package CMAKE_%s_COMPILER -> %s)"
                    % (lang, replacement)
                )
        if content != orig:
            try:
                with open(path, "w", encoding="utf-8", errors="surrogateescape") as handle:
                    handle.write(content)
            except OSError:
                pass
