#!/usr/bin/env python3
"""Conan recipe \u2014 libnu 1.11.1 (nunicode, CMake, C99 static library).

libnu is a small C99 i18n library implementing Unicode 13.0 (UTF-8/16/32,
cesu8, case mapping, collation, normalization helpers). Upstream builds a
single static target `nu` plus an optional `units` test binary
(tests/CMakeLists.txt, enabled with NU_BUILD_TESTS=ON).

Upstream test surface: tests/*_test.c assert-based modules executed through
one `units` binary (exit 0 + `OK - N tests` = all asserts passed). build()
configures with NU_BUILD_TESTS=ON, builds, locates the real `units` binary
under the build tree, runs it capturing stdout, parses the `OK - N tests`
summary for HMBS_UPSTREAM_TEST_RESULT counts (no hardcoded pass). Evidence is
persisted to res/upstream_test_result.json so test_package re-emits the
exact numbers on every run (including cached "Already installed" runs).
"""
import glob
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, collect_libs, copy, export_conandata_patches, get, rm, rmdir


class LibnuConan(ConanFile):
    name = "libnu"
    version = "1.11.1"
    description = "Small C99 Unicode library (UTF-8/16/32, casemap, collation)"
    license = "MIT"
    homepage = "https://bitbucket.org/alekseyt/nunicode"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("unicode", "i18n", "utf8", "utf16", "utf32")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream test suite switch (tests/CMakeLists.txt builds `units`).
        tc.variables["NU_BUILD_TESTS"] = "ON"
        tc.variables["NU_BUILD_SAMPLES"] = "OFF"
        # HMBS_LOW_MEM_RELEASE_O1:真机 compile 阶段曾报 `/bin/sh: Out of
        # memory`。根因是 Release 默认 -O3 编译巨型 Unicode 表时峰值内存
        # 超限:tests/gen/_ducet_test.c(1.1MB)+libnu/gen/_ducet.c(544KB)。
        # 上游原本只在 Debug(-O0)下构建 tests,内存很低;本配方为保住
        # libnu.a 命名而保持 Release,却把优化提到了 -O3。降为 -O1+DNDEBUG
        # 保留 Release 语义,仅削减优化器内存。不跳过任何测试。
        tc.variables["CMAKE_C_FLAGS_RELEASE"] = "-O1 -DNDEBUG"
        tc.variables["CMAKE_CXX_FLAGS_RELEASE"] = "-O1 -DNDEBUG"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._patch_sources_for_conan()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not can_run(self):
            self.output.info("cross-building: skip upstream units run")
            return
        result = self._run_upstream_tests()
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        evidence_dir = os.path.join(self.build_folder, "upstream")
        os.makedirs(evidence_dir, exist_ok=True)
        with open(os.path.join(evidence_dir, "upstream_test_result.json"),
                  "w", encoding="utf-8") as f:
            json.dump(result, f)
        if result["status"] != "passed":
            raise ConanException(
                "upstream units tests failed: "
                "{}/{} passed".format(result["passed"], result["discovered"]))

    def _patch_sources_for_conan(self):
        # HMBS_KEEP_TOOLCHAIN_BUILD_TYPE: upstream forces Debug whenever
        # NU_BUILD_TESTS=ON, which renames the installed lib to libnud.a
        # (DEBUG_POSTFIX d) while cpp_info.libs == ["nu"], so CMakeDeps
        # fails with "Library 'nu' not found in package". Keep the
        # toolchain build_type (Release stays Release) so the artifact is
        # always libnu.a; the assert-based `units` binary runs fine in
        # Release. Also honor BUILD_SHARED_LIBS and drop the Debug postfix.
        top = os.path.join(self.source_folder, "CMakeLists.txt")
        try:
            with open(top, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            return
        if "HMBS_KEEP_TOOLCHAIN_BUILD_TYPE" in content:
            pass
        else:
            anchor = 'set(CMAKE_BUILD_TYPE "Debug")'
            if anchor in content:
                content = content.replace(
                    anchor,
                    '# HMBS_KEEP_TOOLCHAIN_BUILD_TYPE: keep Conan toolchain '
                    'build_type (do not force Debug)\n'
                    '# set(CMAKE_BUILD_TYPE "Debug")')
                content = content.replace(
                    'set(CMAKE_CONFIGURATION_TYPES "Debug") # restrict configurations to Debug',
                    '# HMBS_KEEP_TOOLCHAIN_BUILD_TYPE: keep all toolchain configurations')
                with open(top, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                self.output.info("HMBS patch: forced-Debug anchor not found, skip")
        lib_cmake = os.path.join(self.source_folder, "libnu", "CMakeLists.txt")
        try:
            with open(lib_cmake, "r", encoding="utf-8", errors="replace") as f:
                lc = f.read()
        except OSError:
            return
        orig = lc
        if "add_library(nu STATIC" in lc:
            lc = lc.replace("add_library(nu STATIC", "add_library(nu")
        # HMBS: drop the Debug postfix so the artifact stays libnu.a in all
        # configs (otherwise cpp_info.libs == ["nu"] cannot find libnud.a).
        # NOTE: must not append a trailing `#` comment on the same line: in
        # CMake `#` comments out the rest of the line including the closing
        # `)`, which breaks parsing with `Function missing ending ")"`.
        if "HMBS_KEEP_LIBNU_POSTFIX" in lc:
            pass
        elif "set_target_properties(nu PROPERTIES DEBUG_POSTFIX d)" in lc:
            lc = lc.replace(
                "set_target_properties(nu PROPERTIES DEBUG_POSTFIX d)",
                "# HMBS_KEEP_LIBNU_POSTFIX: keep lib name 'nu' in all configs\n"
                "set_target_properties(nu PROPERTIES DEBUG_POSTFIX \"\")")
        # HMBS_KEEP_CONTRACTIONS: upstream defines NU_DISABLE_CONTRACTIONS in
        # Release/PROF, which removes _nu_ducet_weight_switch from libnu
        # while tests/gen/_ducet_switch_test.c still references it. Upstream
        # only builds tests in Debug (top CMake forces Debug when
        # NU_BUILD_TESTS=ON). We keep the Conan toolchain build_type
        # (Release) for packaging, so drop the Release-only disable to keep
        # lib and tests in agreement (contractions enabled, slightly larger
        # but correct).
        if "HMBS_KEEP_CONTRACTIONS" in lc:
            pass
        elif "NU_DISABLE_CONTRACTIONS" in lc:
            lc = lc.replace(
                "$<$<OR:$<CONFIG:Release>,$<CONFIG:PROF>>:NU_DISABLE_CONTRACTIONS>",
                "# HMBS_KEEP_CONTRACTIONS: keep contractions in all configs "
                "so Release units link")
        if lc != orig:
            with open(lib_cmake, "w", encoding="utf-8") as f:
                f.write(lc)
        self._patch_low_mem_sources()

    def _patch_low_mem_sources(self):
        # HMBS_LOW_MEM_O1 (belt-and-braces for the toolchain -O1 above):
        # force -O1 on the giant generated translation units so even if the
        # toolchain Release flags are overridden, clang never runs -O3 over
        # the 1.1MB tests/gen/_ducet_test.c / 544KB libnu/gen/_ducet.c on a
        # small-memory真机. Idempotent via marker; test logic untouched.
        tests_cmake = os.path.join(self.source_folder, "tests", "CMakeLists.txt")
        try:
            with open(tests_cmake, "r", encoding="utf-8", errors="replace") as f:
                tc_content = f.read()
        except OSError:
            tc_content = None
        if tc_content is not None and "HMBS_LOW_MEM_O1" not in tc_content:
            tc_content += (
                "\n# HMBS_LOW_MEM_O1: giant generated tables OOM with -O3 on "
                "low-memory builders; cap these TUs at -O1.\n"
                "if(CMAKE_C_COMPILER_ID MATCHES \"GNU|Clang|AppleClang\")\n"
                "  set_source_files_properties(gen/_ducet_test.c "
                "gen/_ducet_switch_test.c "
                "gen/_ducet_compact_test.c "
                "gen/_ducet_switch_compact_test.c "
                "PROPERTIES COMPILE_OPTIONS \"-O1\")\n"
                "endif()\n"
            )
            with open(tests_cmake, "w", encoding="utf-8") as f:
                f.write(tc_content)
        lib_cmake2 = os.path.join(self.source_folder, "libnu", "CMakeLists.txt")
        try:
            with open(lib_cmake2, "r", encoding="utf-8", errors="replace") as f:
                lc2 = f.read()
        except OSError:
            return
        if "HMBS_LOW_MEM_O1" not in lc2:
            lc2 += (
                "\n# HMBS_LOW_MEM_O1: giant generated tables OOM with -O3 on "
                "low-memory builders; cap these TUs at -O1.\n"
                "if(CMAKE_C_COMPILER_ID MATCHES \"GNU|Clang|AppleClang\")\n"
                "  set_source_files_properties(gen/_ducet.c "
                "gen/_ducet_switch.c "
                "gen/_ducet_compact.c "
                "gen/_ducet_switch_compact.c "
                "PROPERTIES COMPILE_OPTIONS \"-O1\")\n"
                "endif()\n"
            )
            with open(lib_cmake2, "w", encoding="utf-8") as f:
                f.write(lc2)

    def _discover_upstream_tests(self):        # Audited sources: tests/*_test.c modules + 2 generated ducet files.
        # Count from the real source tree so drift fails loudly instead of
        # silently passing with a stale number.
        pattern = os.path.join(self.source_folder, "tests", "*_test.c")
        files = sorted(glob.glob(pattern))
        # Exclude helpers without test bodies if present.
        mods = [f for f in files
                if os.path.basename(f) not in ("switch_test_base.c",)]
        # main.c is the driver, not a module; _test count + 2 gen modules.
        mods = [f for f in mods if os.path.basename(f) != "main.c"]
        gen_extra = 2
        return mods, gen_extra

    def _find_units(self):
        cands = []
        for pat in ("units", "units.exe", "**/units", "**/units.exe"):
            cands += glob.glob(os.path.join(self.build_folder, pat),
                               recursive=True)
        for c in cands:
            if os.path.isfile(c):
                return c
        # cmake_layout build dir fallback walk
        for root, _ds, fs in os.walk(self.build_folder):
            if "units" in fs:
                return os.path.join(root, "units")
            if "units.exe" in fs:
                return os.path.join(root, "units.exe")
        return None

    def _run_upstream_tests(self):
        mods, gen_extra = self._discover_upstream_tests()
        discovered = len(mods) + gen_extra
        units = self._find_units()
        if units is None:
            return {
                "status": "failed",
                "framework": "units",
                "command": "build tests/units (NU_BUILD_TESTS=ON) and run it",
                "discovered": discovered,
                "executed": 0,
                "passed": 0,
                "failed": discovered,
                "skipped": 0,
                "reason": "units binary not found under build folder",
            }
        if os.path.getsize(units) == 0:
            return {
                "status": "failed",
                "framework": "units",
                "command": units,
                "discovered": discovered,
                "executed": 0,
                "passed": 0,
                "failed": discovered,
                "skipped": 0,
                "reason": "units binary is empty",
            }
        # Real execution: assert harness exits non-zero on any failure.
        # Capture stdout to a log so the reported counts come from the real
        # `OK - N tests` line instead of the file-based module estimate.
        # This keeps the marker consistent with the log (preflight showed
        # `OK - 103 tests` while the marker said 24 modules) and fails
        # loudly on empty output (no silent pass on an empty binary).
        log_path = os.path.join(self.build_folder, "upstream", "units.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.run('"{units}" > "{log}" 2>&1'.format(units=units, log=log_path))
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        self.output.info("units output:\n" + out)
        if not out.strip():
            return {
                "status": "failed",
                "framework": "units",
                "command": "build tests/units (NU_BUILD_TESTS=ON) and run it",
                "discovered": discovered,
                "executed": 0,
                "passed": 0,
                "failed": discovered,
                "skipped": 0,
                "reason": "units produced empty output",
            }
        m = re.search(r"OK\s*-\s*(\d+)\s*tests", out)
        if m:
            total = int(m.group(1))
            if total <= 0:
                return {
                    "status": "failed",
                    "framework": "units",
                    "command": "build tests/units (NU_BUILD_TESTS=ON) and run it",
                    "discovered": discovered,
                    "executed": 0,
                    "passed": 0,
                    "failed": discovered,
                    "skipped": 0,
                    "reason": "units reported non-positive count: {}".format(out.strip()[-200:]),
                }
        else:
            # No summary line: fall back to module estimate but mark failed
            # so a harness change never silently passes with stale numbers.
            return {
                "status": "failed",
                "framework": "units",
                "command": "build tests/units (NU_BUILD_TESTS=ON) and run it",
                "discovered": discovered,
                "executed": discovered,
                "passed": 0,
                "failed": discovered,
                "skipped": 0,
                "reason": "units output missing 'OK - N tests' summary",
            }
        return {
            "status": "passed",
            "framework": "units",
            "command": "build tests/units (NU_BUILD_TESTS=ON) and run it",
            "discovered": total,
            "executed": total,
            "passed": total,
            "failed": 0,
            "skipped": 0,
        }

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Drop upstream's own CMake config so downstream find_package()
        # unambiguously uses Conan's CMakeDeps files (avoids dual
        # nunicode-config.cmake shadowing).
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rm(self, "*.cmake", os.path.join(self.package_folder, "lib"),
           recursive=True)
        # Robust artifact recovery: cmake.install() should place libnu.a
        # (or shared equivalent) under lib/. If it is missing (export
        # quirk, layout drift, postfix rename), walk the whole build tree
        # with os.walk and copy the real artifact manually, so CMakeDeps
        # can always resolve the declared libs entry.
        libdir = os.path.join(self.package_folder, "lib")
        try:
            before = sorted(os.listdir(libdir)) if os.path.isdir(libdir) else []
        except OSError:
            before = []
        self.output.info("HMBS package lib before fallback: {}".format(before))
        have_lib = False
        try:
            if os.path.isdir(libdir):
                for n in os.listdir(libdir):
                    if os.path.isfile(os.path.join(libdir, n)):
                        have_lib = True
                        break
        except OSError:
            have_lib = False
        if not have_lib:
            copy(self, "*.h", src=os.path.join(self.source_folder, "libnu"),
                 dst=os.path.join(self.package_folder, "include", "libnu"))
            found = []
            for root, _ds, fs in os.walk(self.build_folder):
                for fn in fs:
                    ln = fn.lower()
                    if ln.startswith("libnu") or ln.startswith("nu"):
                        if ln.endswith((".a", ".so", ".dylib", ".lib", ".dll")):
                            found.append(os.path.join(root, fn))
            # Also accept versioned .so (libnu.so.X.Y) which endswith digits.
            if not found:
                for root, _ds, fs in os.walk(self.build_folder):
                    for fn in fs:
                        if "nu" in fn.lower() and (".so" in fn or ".dylib" in fn):
                            found.append(os.path.join(root, fn))
            self.output.info(
                "HMBS package fallback candidates: {}".format(found))
            import shutil
            os.makedirs(libdir, exist_ok=True)
            for src_file in found:
                try:
                    shutil.copy2(src_file,
                                os.path.join(libdir, os.path.basename(src_file)))
                except OSError as e:
                    self.output.warning(
                        "HMBS fallback copy failed {}: {}".format(src_file, e))
            # Normalize Debug-postfix artifact (libnud.a) to libnu.a so
            # cpp_info.libs == ["nu"] resolves in every configuration.
            try:
                entries = os.listdir(libdir) if os.path.isdir(libdir) else []
            except OSError:
                entries = []
            if "libnu.a" not in entries and "nu.lib" not in entries:
                for alias_src, alias_dst in (("libnud.a", "libnu.a"),
                                             ("nud.lib", "nu.lib")):
                    s = os.path.join(libdir, alias_src)
                    d = os.path.join(libdir, alias_dst)
                    if os.path.isfile(s) and not os.path.isfile(d):
                        try:
                            shutil.copy2(s, d)
                            self.output.info(
                                "HMBS normalized {} -> {}".format(
                                    alias_src, alias_dst))
                        except OSError as e:
                            self.output.warning(
                                "HMBS normalize failed: {}".format(e))
            try:
                after = sorted(os.listdir(libdir)) if os.path.isdir(libdir) else []
            except OSError:
                after = []
            self.output.info("HMBS package lib after fallback: {}".format(after))
            if not any(os.path.isfile(os.path.join(libdir, n)) for n in after):
                raise ConanException(
                    "package() produced no library file under lib/: "
                    "before={} after={} searched={}".format(before, after, found))
        copy(self, "upstream_test_result.json",
             src=os.path.join(self.build_folder, "upstream"),
             dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        # Adapt to the real artifact: normally ["nu"] (libnu.a). If the
        # packaged file drifted (e.g. debug postfix libnud.a), follow the
        # actual file so CMakeDeps never emits "Library not found".
        try:
            detected = collect_libs(self)
        except Exception:
            detected = []
        if "nu" in detected or not detected:
            self.cpp_info.libs = ["nu"]
        else:
            # Prefer a libnu* artifact when several files exist.
            nu_like = [l for l in detected if "nu" in l.lower()]
            self.cpp_info.libs = nu_like or detected
        self.cpp_info.set_property("cmake_file_name", "nunicode")
        self.cpp_info.set_property("cmake_target_name", "nunicode::nu")
        self.cpp_info.set_property("pkg_config_name", "libnu")
        # HMBS_KEEP_CONSUMER_DEFINES: upstream exposes its whole API behind
        # NU_WITH_EVERYTHING (libnu/config.h gates every nu_utf8/utf16/
        # validate/version declaration). Upstream propagates it via
        # target_compile_definitions(nu PUBLIC ...), but package() removes
        # lib/cmake/nunicode so downstream must use Conan's CMakeDeps files.
        # Re-export the define here or test_package sees only implicit
        # declarations (nu_utf8_read undeclared, nu_utf8_validread unknown).
        self.cpp_info.defines = ["NU_WITH_EVERYTHING"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
