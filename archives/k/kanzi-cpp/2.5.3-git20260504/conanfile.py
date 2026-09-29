#!/usr/bin/env python3
"""Conan recipe for kanzi-cpp 2.5.3-git20260504 on HarmonyOS PC.

Kanzi (https://github.com/flanglet/kanzi-cpp) is a modern, modular and
portable lossless data compressor written in C++ (Apache-2.0). CMake
build, C++17, requires Threads.

OHOS-specific adaptations:
- KANZI_ENABLE_NATIVE_OPTIMIZATIONS=OFF. Upstream defaults this option to
  ON, which appends -march=native to the compile flags. It is disabled so
  the packaged binaries target generic armv8 and stay reproducible across
  machines.
- patches/testapi-tmpfile-tmpdir.patch: TestAPI portable_fmemopen() uses
  tmpfile() which hardcodes /tmp and ignores $TMPDIR, returning NULL on
  HarmonyOS workers (API ctest aborts at "fmemopen failed", TestAPI.c:106).
  The patch keeps tmpfile() as the primary path and adds a
  TMPDIR/TMP/TEMP-aware mkstemp fallback (unlinked immediately to keep
  tmpfile anonymity). Test semantics unchanged, no assertion weakened.
- Upstream registers its 8 ctest entries unconditionally (no test option
  exists); build() runs them with ctest and emits the
  HMBS_UPSTREAM_TEST_RESULT marker. Counts are parsed deterministically
  from Testing/Temporary/LastTest.log (single source: one "Testing:"
  header per test plus its "Test Passed/Failed" verdict line).
- Upstream always builds both the static (libkanzi.a) and the shared
  (libkanzi.so) library plus the kanzi/kanzi_static command line tools.
  Conan requires package_type="library" to declare a `shared` option, so
  this recipe declares options.shared (default False); both libraries are
  packaged regardless of its value.
- OHOS low-memory mitigation: upstream hardcodes -O3 in COMMON_FLAGS
  (appended after toolchain flags, so toolchain -O1 loses). source()
  downgrades it in place to -O1 -g0 on OHOS only, complementing the
  additive toolchain/build-env -O1 -g0 appends. build() additionally
  caps cmake --build at one job on OHOS (CI fork-OOM guard).
  No test skipped.
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class KanziCppConan(ConanFile):
    name = "kanzi-cpp"
    version = "2.5.3-git20260504"
    description = "Fast lossless data compression in C++"
    license = "Apache-2.0"
    homepage = "https://github.com/flanglet/kanzi-cpp"
    url = "https://github.com/flanglet/kanzi-cpp"
    package_type = "library"

    # Conan 2 hard check: package_type="library" must declare a `shared`
    # option ("Package type is 'library', but no 'shared' option declared").
    # Upstream always builds both static (libkanzi.a) and shared
    # (libkanzi.so); both are packaged regardless of this option's value.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # HMBS OOM adaptation (OHOS only): upstream hardcodes
        # "-O3" in COMMON_FLAGS inside CMakeLists.txt, which is appended
        # AFTER the toolchain/profile flags. The generate()/build()
        # "-O1 -g0" appends therefore lose (final flags end with -O3),
        # so a low-memory device still compiles every TU at -O3 and dies
        # with Signal 9. Downgrade the upstream flag in place to -O1 -g0
        # (warnings/PIC/NDEBUG untouched, no test or lib output skipped).
        # Conan 2 forbids self.settings access in source(), so apply
        # unconditionally: this recipe only targets OHOS/Linux and the
        # replacement is a no-op when the upstream flag text is absent.
        try:
            cmake_lists = os.path.join(self.source_folder,
                                       "CMakeLists.txt")
            with open(cmake_lists, "r", encoding="utf-8",
                      errors="replace") as handle:
                content = handle.read()
            orig = content
            needle = '"-Wall -Wextra -O3'
            repl = '"-Wall -Wextra -O1 -g0'
            if needle in content:
                content = content.replace(needle, repl)
            elif " -O3" in content:
                content = content.replace(" -O3", " -O1 -g0")
            if content != orig:
                with open(cmake_lists, "w",
                          encoding="utf-8") as handle:
                    handle.write(content)
                self.output.info(
                    "HMBS diag downgraded upstream -O3 to -O1 -g0 in %s"
                    % cmake_lists)
        except Exception as exc:
            self.output.warning(
                "HMBS diag upstream -O flag downgrade failed: %s" % exc)

    def _resolve_compiler(self, configured, names):
        # Profile points at /data/service/hnp/bin/clang which is missing
        # or not executable on some preflight workers (compiler
        # identification unknown); prefer the configured path only when
        # it exists, else resolve via PATH / ~/usr/local/bin fallback.
        if configured and os.path.isfile(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local",
                                "bin")
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.isfile(cand):
                return cand
        return configured or names[0]

    def _usable_compilers(self):
        try:
            compilers = self.conf.get("tools.build:compiler_executables",
                                      default={}, check_type=dict) or {}
        except Exception:
            compilers = {}
        cc = self._resolve_compiler(compilers.get("c"), ("clang", "cc"))
        cxx = self._resolve_compiler(compilers.get("cpp"),
                                     ("clang++", "c++"))
        if compilers.get("c") and cc != compilers.get("c"):
            self.output.warning(
                "profile C compiler '%s' unusable, using '%s' instead"
                % (compilers.get("c"), cc))
        if compilers.get("cpp") and cxx != compilers.get("cpp"):
            self.output.warning(
                "profile C++ compiler '%s' unusable, using '%s' instead"
                % (compilers.get("cpp"), cxx))
        return cc, cxx

    def _fix_generated_toolchain_compiler(self, configured_map, c, cxx):
        # Third-round fix: cache_variables + configure(variables=) both
        # failed to override the stale profile compiler (preflight log
        # shows harmonybrew resolved yet project() still uses
        # /data/service/hnp/bin/clang). Rewrite the generated
        # conan_toolchain.cmake in place and export CC/CXX in build
        # scope (zydis/4.1.1 precedent). Only when configured path is
        # missing and resolved one exists.
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
                          errors="replace") as handle:
                    text = handle.read()
                orig = text
                for old_p, new_p in pairs:
                    text = text.replace(old_p, new_p)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(text)
                    self.output.info(
                        "HMBS diag fixed generated toolchain %s" % path)
                for line in text.splitlines():
                    s = line.strip()
                    if "CMAKE_C_COMPILER" in s or "CMAKE_CXX_COMPILER" in s:
                        self.output.info("HMBS diag toolchain %s" % s)
        except Exception as exc:
            self.output.warning("HMBS diag toolchain fix failed: %s" % exc)
        try:
            comp_env = Environment()
            if c_old and c and (c_old, c) in pairs:
                comp_env.define("CC", c)
            if cxx_old and cxx and (cxx_old, cxx) in pairs:
                comp_env.define("CXX", cxx)
            comp_env.vars(self, scope="build").save_sh("hmbs_compiler")
        except Exception as exc:
            self.output.warning(
                "HMBS diag compiler env export failed: %s" % exc)

    def _append_oom_flags_to_toolchain(self):
        # Low-memory device mitigation, second half: append -O1 -g0 to
        # the generated conan_toolchain.cmake tail behind an idempotent
        # marker. generate()-time extra_cflags already covers the
        # initial toolchain content, but build() re-appends here so a
        # regenerated toolchain (compiler fix above rewrites the file)
        # cannot lose the flags. Additive only: string(APPEND ...)
        # after profile flags, trailing -O1 wins, -g0 strips debug
        # info. Upstream tests and lib outputs unchanged.
        if str(self.settings.os) != "OHOS":
            return
        try:
            gf = getattr(self, "generators_folder", None)
            path = os.path.join(gf, "conan_toolchain.cmake") if gf else None
            if not path or not os.path.isfile(path):
                return
            marker = "HMBS_OOM_MITIGATION"
            with open(path, "r", encoding="utf-8",
                      errors="replace") as handle:
                text = handle.read()
            if marker in text:
                return
            text += "\n# " + marker + ": low-memory device, append only,\n"
            text += "# do not overwrite profile flags\n"
            text += 'string(APPEND CMAKE_C_FLAGS " -O1 -g0")\n'
            text += 'string(APPEND CMAKE_CXX_FLAGS " -O1 -g0")\n'
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
            self.output.info("HMBS diag appended OOM flags to %s" % path)
        except Exception as exc:
            self.output.warning("HMBS diag OOM toolchain append failed: %s"
                                % exc)

    def generate(self):
        tc = CMakeToolchain(self)
        _conf_compilers = {}
        if self.settings.os == "OHOS":
            # E092: vanilla CMake has no Platform/HarmonyOS module, so the
            # default CMAKE_SYSTEM_NAME=HarmonyOS makes project() fail
            # ("System is unknown to cmake" + compiler check broken).
            # HarmonyOS is Linux-kernel compatible for this plain C++17
            # library; alias to Linux (oystr/abcmidi precedent). Must be
            # cache_variables (command-line -D): toolchain set() is too
            # late for the compiler check and cmake_minimum_required.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            # Upstream requires 3.10; device CMake is 4.x which removed
            # <3.5 compat, so pin the minimum explicitly.
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
            # Stale profile compiler pin: generated conan_toolchain.cmake
            # keeps referencing the missing hnp clang even after
            # cache_variables (zydis precedent), so pin the resolved
            # working compiler as well; build() re-pins on the command
            # line too (kyoto-tycoon double-pinning lesson).
            cc, cxx = self._usable_compilers()
            if cc:
                tc.cache_variables["CMAKE_C_COMPILER"] = cc
            if cxx:
                tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx
            self.output.info("HMBS diag compilers c=%s cxx=%s" % (cc, cxx))
            try:
                _conf_compilers = self.conf.get(
                    "tools.build:compiler_executables",
                    default={}, check_type=dict) or {}
            except Exception:
                _conf_compilers = {}
        # Generic armv8 output: do not let upstream inject -march=native.
        tc.variables["KANZI_ENABLE_NATIVE_OPTIMIZATIONS"] = False
        # HMBS low-memory mitigation (true-device OOM: tar fork
        # "Cannot fork: Out of memory" during compile phase): append
        # reduced-optimization and no-debug flags additively without
        # overwriting profile flags. Placed after profile -O3, the
        # trailing -O1 wins in clang/gcc; -g0 strips debug info.
        # Upstream tests and both lib outputs are unchanged.
        for _flag in ("-O1", "-g0"):
            tc.extra_cflags.append(_flag)
            tc.extra_cxxflags.append(_flag)
        if self.settings.os == "OHOS":
            # Build-environment half of the same mitigation: CFLAGS /
            # CXXFLAGS are appended (not defined) so profile flags are
            # preserved; saved as a separate sh script so it composes
            # with the hmbs_compiler script above.
            try:
                oom_env = Environment()
                oom_env.append("CFLAGS", "-O1 -g0")
                oom_env.append("CXXFLAGS", "-O1 -g0")
                oom_env.vars(self, scope="build").save_sh("hmbs_oom_flags")
            except Exception as exc:
                self.output.warning(
                    "HMBS diag OOM env export failed: %s" % exc)
        tc.generate()
        if self.settings.os == "OHOS":
            try:
                _cc = tc.cache_variables.get("CMAKE_C_COMPILER")
            except Exception:
                _cc = None
            try:
                _cxx = tc.cache_variables.get("CMAKE_CXX_COMPILER")
            except Exception:
                _cxx = None
            self._fix_generated_toolchain_compiler(
                _conf_compilers, _cc, _cxx)

    def build(self):
        cc, cxx = self._usable_compilers() if self.settings.os == "OHOS" \
            else (None, None)
        variables = {}
        if cc:
            variables["CMAKE_C_COMPILER"] = cc
        if cxx:
            variables["CMAKE_CXX_COMPILER"] = cxx
        self._append_oom_flags_to_toolchain()
        cmake = CMake(self)
        cmake.configure(variables=variables)
        if str(self.settings.os) == "OHOS":
            # HMBS OOM mitigation, part 3 (CI #64211 fork failed: out of
            # memory): cap the build itself at one job (oystr precedent:
            # cli_args=["--parallel", "1"], build_tool_args=["-j1"]).
            # HMBS preflight injects tools.build:jobs=1 but the CI worker
            # profile may resolve higher parallelism (-j20 seen on device);
            # an explicit cap keeps peak RSS to a single TU plus a single
            # link regardless of profile. Test execution unchanged.
            cmake.build(cli_args=["--parallel", "1"],
                        build_tool_args=["-j1"])
        else:
            cmake.build()
        self._run_upstream_tests()

    def _find_ctest(self):
        """Locate the ctest executable (HMBS puts tool dirs on PATH)."""
        ctest = shutil.which("ctest")
        if ctest is not None:
            return ctest
        for key in ("HMBS_CMAKE",):
            cmake_bin = os.environ.get(key)
            if cmake_bin:
                cand = os.path.join(os.path.dirname(cmake_bin), "ctest")
                if os.path.isfile(cand):
                    return cand
        try:
            cmake_path = self.conf.get("user.hmbs:cmake_path", check_type=str)
        except Exception:
            cmake_path = None
        if cmake_path:
            cand = os.path.join(os.path.dirname(cmake_path), "ctest")
            if os.path.isfile(cand):
                return cand
        raise RuntimeError("ctest executable not found (checked PATH, "
                           "$HMBS_CMAKE sibling and user.hmbs:cmake_path)")

    def _find_last_test_log(self):
        for root, _dirs, files in os.walk(self.build_folder):
            if "LastTest.log" in files and root.endswith(
                    os.path.join("Testing", "Temporary")):
                return os.path.join(root, "LastTest.log")
        return None

    def _parse_last_test_log(self, path):
        """Parse LastTest.log. Single source: Testing:/verdict lines."""
        discovered = 0
        verdicts = {}
        current = None
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                head = re.match(r"^\s*\d+/\d+\s+Testing:\s+(\S+)", line)
                if head is not None:
                    current = head.group(1)
                    if current not in verdicts:
                        verdicts[current] = None
                        discovered += 1
                    continue
                if current is None:
                    continue
                if re.match(r"^Test Passed\.", line):
                    verdicts[current] = "passed"
                elif re.match(r"^Test (Failed|Timeout)\.", line):
                    verdicts[current] = "failed"
        passed = sum(1 for v in verdicts.values() if v == "passed")
        failed = sum(1 for v in verdicts.values() if v == "failed")
        skipped = discovered - passed - failed
        executed = passed + failed
        return discovered, executed, passed, failed, skipped

    def _run_upstream_tests(self):
        """Run the 8 upstream ctest entries and emit the HMBS marker."""
        ctest = self._find_ctest()
        # OHOS: /system/sh (mksh) cannot execute ELF test binaries directly,
        # so drive ctest through the bash from the build environment.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        env = dict(os.environ)
        env["CTEST_OUTPUT_ON_FAILURE"] = "1"
        cmd = f'cd "{self.build_folder}" && "{ctest}" --output-on-failure'
        proc = subprocess.run([bash, "-c", cmd], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True,
                              timeout=1800, env=env, cwd=self.build_folder)
        self.output.info(f"ctest exit={proc.returncode}\n{proc.stdout[-3000:]}")
        log_path = self._find_last_test_log()
        if log_path is None:
            searched = self.build_folder
            upstream = {
                "status": "failed",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "LastTest.log not found under " + searched,
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                             json.dumps(upstream, ensure_ascii=False))
            raise RuntimeError("upstream ctest produced no LastTest.log")
        discovered, executed, passed, failed, skipped = \
            self._parse_last_test_log(log_path)
        status = "passed" if (failed == 0 and skipped == 0
                              and executed == discovered
                              and executed > 0) else "failed"
        upstream = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                         json.dumps(upstream, ensure_ascii=False))
        if status != "passed":
            raise RuntimeError(
                f"upstream ctest failed: {passed}/{executed} passed, "
                f"{failed} failed, {skipped} skipped "
                f"out of {discovered} (see {log_path})")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["kanzi"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
