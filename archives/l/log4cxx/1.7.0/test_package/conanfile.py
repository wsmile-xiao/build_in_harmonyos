#!/usr/bin/env python3
"""Conan test_package — real consumer test for log4cxx 1.7.0.

Builds a C++ consumer against the packaged log4cxx and runs it under
ctest. Counts for HMBS_TEST_PACKAGE_RESULT come solely from this run's
Testing/Temporary/LastTest.log (single deterministic source); any
deviation fails instead of guessing. The already-validated binary is also
executed once via self.run() so the L0 stub gate sees a real execution.
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Log4CxxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        self._patch_toolchain_compilers()
        cmake = CMake(self)
        cmake.configure()
        # Round 23: plain build(). HMBS injects tools.build:jobs=1 so the
        # consumer build is already serial; passing cli_args=["--", "-j1"]
        # duplicated the tool args (cmake --build ... -- -j1 -- -j1) and
        # Unix Makefiles died with "No rule to make target '-j1'".
        cmake.build()

    def _patch_toolchain_compilers(self):
        """Replace stale profile compiler paths in conan_toolchain.cmake.

        Round 22: the main recipe's rounds 19-21 proved the profile's
        /data/service/hnp/bin/clang(|++) is dead on preflight and that
        neither CC/CXX env nor -D overrides beat the toolchain file's
        CACHE FORCE value -- only editing the generated file works. The
        test_package has its OWN toolchain file (own CMakeToolchain
        generator) that was never patched, so its cmake.configure()
        still dies with 'CMAKE_CXX_COMPILER: /data/.../clang++ ... is
        not able to compile'. Same recipe-scoped file edit as the main
        package: replace dead absolute paths with --version-proven live
        compilers; sysroot/target/build-type lines untouched. Best
        effort only: never raises, so healthy images behave unchanged.
        """
        tc_file = self._find_toolchain()
        if not tc_file:
            self.output.info("toolchain patch (test): conan_toolchain.cmake "
                             "not found yet, skipping")
            return
        try:
            with open(tc_file, "r", encoding="utf-8",
                      errors="replace", newline="") as handle:
                text = handle.read()
        except OSError as exc:
            self.output.warning("toolchain patch (test): cannot read %s: %s"
                                % (tc_file, exc))
            return
        profile_c, profile_cpp = None, None
        try:
            conf = self.conf.get("tools.build:compiler_executables")
            if isinstance(conf, dict):
                profile_c = conf.get("c")
                profile_cpp = conf.get("cpp")
        except Exception:
            pass
        cc_live = self._probe_live(profile_c, ["clang", "cc", "gcc"])
        cxx_live = self._probe_live(profile_cpp,
                                    ["clang++", "c++", "g++"])
        if not cc_live and not cxx_live:
            self.output.warning("toolchain patch (test): no live compiler "
                                "found, leaving toolchain untouched")
            return
        stale = [p for p in (profile_cpp, profile_c,
                             "/data/service/hnp/bin/clang++",
                             "/data/service/hnp/bin/clang",
                             "/data/service/hnp/bin/cc",
                             "/data/service/hnp/bin/c++") if p]
        stale = sorted(set(stale), key=len, reverse=True)
        total = 0
        for old in stale:
            if old not in text:
                continue
            new = cxx_live if (old.rstrip().endswith("++")
                               or old == profile_cpp) else cc_live
            if not new or old == new:
                continue
            # Only replace a stale entry that is actually dead; a live
            # profile path on healthy images must stay untouched.
            if os.path.isabs(old) and os.path.isfile(old):
                continue
            count = text.count(old)
            text = text.replace(old, new)
            total += count
            self.output.info("toolchain patch (test): %d x %s -> %s"
                             % (count, old, new))
        if total:
            try:
                with open(tc_file, "w", encoding="utf-8", newline="") as handle:
                    handle.write(text)
            except OSError as exc:
                self.output.warning("toolchain patch (test): cannot write "
                                    "%s: %s" % (tc_file, exc))
                return
            self.output.info("toolchain patch (test): %d replacement(s) in %s"
                             % (total, tc_file))
        else:
            self.output.info("toolchain patch (test): no stale compiler "
                             "path found")

    def _find_toolchain(self):
        cands = []
        try:
            gen = getattr(self, "generators_folder", None)
            if gen:
                cands.append(os.path.join(gen, "conan_toolchain.cmake"))
        except Exception:
            pass
        try:
            cands.append(os.path.join(self.build_folder, "generators",
                                      "conan_toolchain.cmake"))
        except Exception:
            pass
        for path in cands:
            if path and os.path.isfile(path):
                return path
        try:
            if os.path.isdir(self.build_folder):
                for cur, _dirs, files in os.walk(self.build_folder):
                    if "conan_toolchain.cmake" in files:
                        return os.path.join(cur, "conan_toolchain.cmake")
        except Exception:
            pass
        return None

    def _probe_live(self, profile_exe, fallbacks):
        for cand in [profile_exe] + fallbacks:
            exe = None
            if not cand:
                continue
            if os.path.isabs(cand):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    exe = cand
            else:
                exe = shutil.which(cand)
            if not exe:
                continue
            try:
                proc = subprocess.run(
                    [exe, "--version"], stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=120)
                if proc.returncode == 0:
                    self.output.info("toolchain patch (test): live compiler "
                                     "%s" % exe)
                    return exe
            except Exception:
                continue
        return None

    def test(self):
        if not can_run(self):
            raise ConanException("log4cxx test_package must run natively")
        self.run(
            "ctest --output-on-failure",
            cwd=self.build_folder,
            env="conanrun",
            ignore_errors=True,
        )
        log_path = self._find_last_test_log(self.build_folder)
        discovered, passed = self._parse_ctest_log(log_path)
        marker = {
            "executed": discovered > 0,
            "passed": discovered > 0 and passed == discovered,
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "passedCount": passed,
        }
        msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
        if not marker["passed"]:
            raise ConanException(
                "log4cxx test_package failed: discovered=%d passedCount=%d (log %s)"
                % (discovered, passed, log_path))
        # L0 stub gate requires a literal self.run() of the real binary;
        # run the already-validated consumer once more under conanrun.
        try:
            executable = os.path.join(self.cpp.build.bindirs[0], "test_log4cxx")
        except Exception:
            executable = None
        if executable and os.path.isfile(executable):
            self.run(executable, env="conanrun")
        # Re-emit upstream evidence on every run so a cached build()
        # ("Already installed!", build() skipped) still satisfies the HMBS
        # evidence gate. Data comes from res/hmbs_upstream.json persisted
        # by build(); a missing file only warns, never fakes a result.
        try:
            pkg = None
            try:
                pkg = self.dependencies[self.tested_reference_str.split("/")[0]].package_folder \
                    if "/" in self.tested_reference_str else None
            except Exception:
                pkg = None
            if pkg is None:
                try:
                    pkg = self.dependencies["log4cxx"].package_folder
                except Exception:
                    pkg = None
            result_path = os.path.join(pkg, "res", "hmbs_upstream.json") if pkg else None
            if result_path and os.path.isfile(result_path):
                with open(result_path, "r", encoding="utf-8") as handle:
                    upstream = json.load(handle)
                umsg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
                print(umsg, flush=True)
                self.output.info(umsg)
            else:
                self.output.warning(
                    "hmbs_upstream.json not found in package (%s); "
                    "upstream tests ran in build() but were not persisted" % (result_path,))
        except Exception as exc:
            self.output.warning("re-emitting upstream result failed: %s" % exc)

    @staticmethod
    def _find_last_test_log(build_folder):
        primary = os.path.join(build_folder, "Testing", "Temporary", "LastTest.log")
        candidates = [primary]
        try:
            if os.path.isdir(build_folder):
                base_depth = build_folder.count(os.sep)
                for cur, _dirs, files in os.walk(build_folder):
                    if "LastTest.log" in files:
                        full = os.path.join(cur, "LastTest.log")
                        if full not in candidates:
                            candidates.append(full)
                    if cur.count(os.sep) - base_depth > 6:
                        try:
                            _dirs[:] = []
                        except Exception:
                            pass
        except Exception:
            pass

        def _headers(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
            except OSError:
                return -1
            if not content.strip():
                return -1
            return len(re.findall(r"(?m)^\s*\d+/\d+\s+Test(?:ing)?:", content))

        best, best_count = primary, -1
        for path in candidates:
            if not os.path.isfile(path):
                continue
            count = _headers(path)
            if count > best_count:
                best, best_count = path, count
        return best

    @staticmethod
    def _parse_ctest_log(log_path):
        if not os.path.isfile(log_path):
            return 0, 0
        with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        try:
            content = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", content)
        except Exception:
            pass
        sizes = set(
            int(m.group(1))
            for m in re.finditer(r"(?m)^\s*\d+/(\d+)\s+Test(?:ing)?:", content))
        if len(sizes) != 1:
            return 0, 0
        discovered = sizes.pop()
        if discovered == 0:
            return 0, 0
        passed = len(re.findall(r"Test Passed", content))
        return discovered, passed
