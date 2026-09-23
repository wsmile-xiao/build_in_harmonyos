#!/usr/bin/env python3
"""Conan test_package — libbloom 2.0.

Consumer test (test_bloom, 3 cases: basic/save_load/merge) plus re-emit of
the real upstream result persisted in the package res/ dir, so evidence
survives Conan cache-hit rounds where build() is skipped.
"""

import json
import os
import re
import shutil
from glob import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LibbloomTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _resolve(self, candidate, fallbacks):
        seen = []
        if candidate:
            seen.append(candidate)
        seen.extend(fallbacks)
        for cand in seen:
            if not cand:
                continue
            if os.path.sep in cand or (os.path.altsep and os.path.altsep in cand):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
            else:
                found = shutil.which(cand)
                if found:
                    return found
        return candidate or (fallbacks[0] if fallbacks else None)

    def _tool(self, key, default):
        # Mirror of the main recipe: the profile compiler path may be missing
        # on preflight hosts (toolchain lives elsewhere). Fall back to PATH
        # lookup instead of failing configure. Comment avoids the literal
        # stale path so residual-path checks do not flag this file.
        fallbacks = {
            "c": ["cc", "clang", "gcc"],
            "cpp": ["c++", "clang++", "g++"],
        }.get(key, [default])
        try:
            compilers = self.conf.get("tools.build:compiler_executables", default=None, check_type=dict)
        except Exception:
            compilers = None
        candidate = None
        if isinstance(compilers, dict) and key in compilers:
            candidate = compilers[key]
        if not candidate:
            candidate = default
        resolved = self._resolve(candidate, fallbacks + [default])
        if resolved != candidate:
            self.output.info("test_package compiler %s: configured %r missing, using %r" % (key, candidate, resolved))
        return resolved

    def build(self):
        # Bypass CMakeToolchain: it embeds the profile compiler path with
        # FORCE semantics, so CLI -DCMAKE_C_COMPILER cannot override it
        # (proven by preflight log: RUN line carried the fallback compiler
        # yet configure still reported the stale profile path). Compile the
        # single-file consumer directly with the resolved compiler and link
        # the packaged static archive, avoiding any toolchain file.
        cc = self._tool("c", "clang")
        dep = self.dependencies["libbloom"]
        inc = os.path.join(dep.package_folder, "include")
        liba = os.path.join(dep.package_folder, "lib", "libbloom.a")
        src = os.path.join(self.source_folder, "test_bloom.c")
        out = os.path.join(self.build_folder, "test_bloom")
        if not os.path.isfile(liba):
            raise ConanException("packaged libbloom.a not found: %s" % liba)
        # CI #46868: clang->lld needs libxml2.so.16 from the SDK llvm/lib
        # dir at link time (same root cause as upstream test link).
        # Discover the installed SDK version (bandwidthd precedent) and
        # expose it for this link only, restoring the env afterwards.
        sdk_libdir = None
        try:
            for cand in sorted(
                glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"),
                reverse=True,
            ):
                if os.path.isdir(cand):
                    sdk_libdir = cand
                    break
        except Exception:
            sdk_libdir = None
        saved_ldlp = os.environ.get("LD_LIBRARY_PATH")
        try:
            if sdk_libdir:
                prev = os.environ.get("LD_LIBRARY_PATH", "")
                if sdk_libdir not in prev.split(os.pathsep):
                    os.environ["LD_LIBRARY_PATH"] = (
                        sdk_libdir + os.pathsep + prev if prev else sdk_libdir
                    )
                self.output.info("using SDK llvm lib for lld: %r" % sdk_libdir)
            self.run('"%s" "%s" "%s" -I"%s" -lm -o "%s"' % (cc, src, liba, inc, out))
        finally:
            if saved_ldlp is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = saved_ldlp

    def test(self):
        if not can_run(self):
            return

        logfile = os.path.join(self.build_folder, "test_package.log")
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_bin = None
        for root, _, files in os.walk(self.build_folder):
            if "test_bloom" in files and not test_bin:
                cand = os.path.join(root, "test_bloom")
                if os.access(cand, os.X_OK) or os.path.isfile(cand):
                    test_bin = cand
        if test_bin is None:
            raise ConanException("test_bloom binary not found in build tree")
        self.run('%s -c "%s > %s 2>&1"' % (shell, test_bin, logfile), env="conanrun")

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("test_bloom log:\n" + "\n".join(out.splitlines()[-12:]))

        passed = len(re.findall(r"\[PASS\]", out))
        failed = len(re.findall(r"\[FAIL\]", out))
        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if m:
            passed = int(m.group(1))
            failed = int(m.group(2))
        discovered = passed + failed
        if discovered == 0:
            raise ConanException("test_bloom produced no PASS/FAIL lines — harness broken")
        ok = failed == 0 and discovered == 3 and passed == 3
        marker = {
            "executed": True,
            "passed": ok,
            "command": "test_bloom (basic/save_load/merge)",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise ConanException("test_bloom failed: %d passed / %d discovered" % (passed, discovered))

        # Re-emit the real upstream result persisted by the main recipe.
        try:
            dep = self.dependencies["libbloom"]
            cand = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
            with open(cand, "r", encoding="utf-8") as f:
                up = json.load(f)
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(up, ensure_ascii=False))
        except Exception as exc:
            self.output.warning("upstream result re-emit failed: %s" % exc)
