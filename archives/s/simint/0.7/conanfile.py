#!/usr/bin/env python3
"""Conan recipe for simint 0.7 — Vectorized Electron Repulsion Integrals.

OHOS aarch64 adaptation:
  - CMake build, vectorization forced to scalar for ARM (SSSE3/AVX not available on aarch64)
  - SIMINT_MAXAM=3 on OHOS (f-functions, balances functionality vs OOM on 1GB runner;
    upstream supports up to 7, Linux keeps user option)
  - ENABLE_TESTS ON for upstream validation via ctest
  - R32: settings.os in ("Linux","OHOS"), R26 not needed (not a system same-name lib)
"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, rm
import json
import os
import re
import subprocess

class SimintConan(ConanFile):
    name = "simint"
    version = "0.7"
    description = "Vectorized Electron Repulsion Integrals (Obara-Saika method)"
    license = "BSD-3-Clause"
    homepage = "https://www.bennyp.org/research/simint/"
    url = "https://github.com/simint-chem/simint"
    topics = ("quantum-chemistry", "integrals", "eri", "vectorization")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "vector": ["scalar", "sse", "avx", "avxfma", "scalar-sse", "scalar-avx", "scalar-avxfma"],
        "max_am": [1, 2, 3, 4, 5, 6, 7],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "vector": "scalar",
        "max_am": 3,
    }
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        vector = str(self.options.vector)
        if self.settings.os == "OHOS":
            vector = "scalar"
        tc.variables["SIMINT_VECTOR"] = vector
        max_am = int(self.options.max_am)
        if self.settings.os == "OHOS" and max_am > 3:
            self.output.warning(f"Clamping max_am {max_am} -> 3 for OHOS to avoid OOM")
            max_am = 3
        tc.variables["SIMINT_MAXAM"] = max_am
        tc.variables["ENABLE_TESTS"] = True
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        tc.generate()

    def _patch_tests_for_ctest(self):
        """Register the 4 upstream test executables with CTest and make the
        accuracy tests (test_eri / test_eri_deriv1) reflect pass/fail in their
        exit code.

        Upstream simint builds 4 standalone test executables (test_eri,
        test_eri_deriv1, benchmark_eri, screentest) but ships NO ctest
        registration (no enable_testing()/add_test()), so `ctest -N` reports 0.
        Additionally test_eri / test_eri_deriv1 always return 0 even when a
        quartet is flagged '***' (accuracy failure), so a naked run can never
        fail.  We adapt both so the upstream suite is really executed and its
        outcome is honestly reflected, letting ctest_entries be a valid count
        method (upstream_test_total=4).
        """
        src = self.source_folder

        # 1) top-level CMakeLists.txt: enable CTest when tests are built
        top_cmake = os.path.join(src, "CMakeLists.txt")
        if os.path.exists(top_cmake):
            txt = open(top_cmake, encoding="utf-8", errors="ignore").read()
            if "enable_testing()" not in txt and "add_subdirectory(test)" in txt:
                txt = txt.replace(
                    "if(ENABLE_TESTS)\n    enable_language(CXX)\n    add_subdirectory(test)",
                    "if(ENABLE_TESTS)\n    enable_language(CXX)\n    enable_testing()\n    add_subdirectory(test)",
                )
                open(top_cmake, "w", encoding="utf-8").write(txt)
                self.output.info("Enabled CTest (enable_testing) in top-level CMakeLists.txt")

        # 2) test/CMakeLists.txt: register the 4 executables as CTest tests
        tcmake = os.path.join(src, "test", "CMakeLists.txt")
        if os.path.exists(tcmake):
            txt = open(tcmake, encoding="utf-8", errors="ignore").read()
            if "ADDTEST(screentest screentest.cpp)" in txt and "add_test(NAME test_eri" not in txt:
                reg = (
                    "\n\n"
                    "# ---- HarmonyOS PC adaptation: register upstream tests with CTest ----\n"
                    "# Upstream builds these 4 test executables but registers none with CTest.\n"
                    "# We register them here (with a small basis-set input) so the suite is\n"
                    "# actually executed and counted (upstream_test_total=4, ctest_entries).\n"
                    'set(SIMINT_CTEST_DATA "${CMAKE_SOURCE_DIR}/test/dat/water.sto-3g.mol")\n'
                    "add_test(NAME test_eri        COMMAND test_eri        ${SIMINT_CTEST_DATA})\n"
                    "add_test(NAME test_eri_deriv1 COMMAND test_eri_deriv1 ${SIMINT_CTEST_DATA})\n"
                    "add_test(NAME screentest      COMMAND screentest      ${SIMINT_CTEST_DATA})\n"
                    "add_test(NAME benchmark_eri   COMMAND benchmark_eri   ${SIMINT_CTEST_DATA})\n"
                )
                txt = txt + reg
                open(tcmake, "w", encoding="utf-8").write(txt)
                self.output.info("Registered 4 upstream tests with CTest in test/CMakeLists.txt")

        # 3) test_eri.cpp / test_eri_deriv1.cpp: propagate the '***' accuracy
        #    failure to a non-zero exit code so CTest fails when integrals wrong.
        decl_old = "    // Map containing the errors\n    // QAM -> (absolute error, relative error)\n    ErrorMap errors;"
        decl_new = (
            "    // Map containing the errors\n"
            "    // QAM -> (absolute error, relative error)\n"
            "    ErrorMap errors;\n"
            "    int had_error = 0;  // set when any quartet exceeds accuracy threshold (HarmonyOS PC adaptation)"
        )
        tail_old = (
            '        bool bad = (abserr > 1e-14 && relerr > 1e-8);\n'
            '        printf("  %10.3e  %10.3e  %s\\n", abserr, relerr, bad ? "***" : "");\n'
            "    }\n"
            "\n"
            '    printf("\\n");\n'
            '    printf("Calculated %ld contracted integrals\\n", static_cast<long>(ncont));\n'
            '    printf("\\n");\n'
            "\n"
            "    FreeShellMap(shellmap);\n"
            "    ValeevRef_Finalize();\n"
            "    simint_finalize();\n"
            "\n"
            "    SIMINT_FREE(all_res_simint);\n"
            "    SIMINT_FREE(all_simint_work);\n"
            "    SIMINT_FREE(all_res_valeev);\n"
            "\n"
            "    return 0;\n"
            "}"
        )
        tail_new = (
            '        bool bad = (abserr > 1e-14 && relerr > 1e-8);\n'
            "        if(bad) had_error = 1;\n"
            '        printf("  %10.3e  %10.3e  %s\\n", abserr, relerr, bad ? "***" : "");\n'
            "    }\n"
            "\n"
            '    printf("\\n");\n'
            '    printf("Calculated %ld contracted integrals\\n", static_cast<long>(ncont));\n'
            '    printf("\\n");\n'
            "\n"
            "    FreeShellMap(shellmap);\n"
            "    ValeevRef_Finalize();\n"
            "    simint_finalize();\n"
            "\n"
            "    SIMINT_FREE(all_res_simint);\n"
            "    SIMINT_FREE(all_simint_work);\n"
            "    SIMINT_FREE(all_res_valeev);\n"
            "\n"
            "    if(had_error)\n"
            "    {\n"
            "        fprintf(stderr, \"simint: accuracy validation FAILED (see *** quartets above)\\n\");\n"
            "        return 1;\n"
            "    }\n"
            "    return 0;\n"
            "}"
        )
        for fname in ("test_eri.cpp", "test_eri_deriv1.cpp"):
            p = os.path.join(src, "test", fname)
            if not os.path.exists(p):
                self.output.warning(f"test source not found: {p}")
                continue
            txt = open(p, encoding="utf-8", errors="ignore").read()
            orig = txt
            if "int had_error" not in txt:
                if decl_old in txt:
                    txt = txt.replace(decl_old, decl_new)
                else:
                    self.output.warning(f"decl block not found in {fname}, skipping exit-code patch")
            if "accuracy validation FAILED" not in txt:
                if tail_old in txt:
                    txt = txt.replace(tail_old, tail_new)
                else:
                    self.output.warning(f"tail block not found in {fname}, skipping exit-code patch")
            if txt != orig:
                open(p, "w", encoding="utf-8").write(txt)
                self.output.info(f"Patched {fname} to propagate accuracy failure to exit code")

    def build(self):
        apply_conandata_patches(self)
        for root, _, files in os.walk(self.source_folder):
            if "CMakeLists.txt" in files:
                p = os.path.join(root, "CMakeLists.txt")
                try:
                    txt = open(p, encoding="utf-8", errors="ignore").read()
                    orig = txt
                    def _bump(m):
                        ver = m.group(1)
                        try:
                            major, minor = (ver.split(".") + ["0"])[:2]
                            major = int(major); minor = int(minor)
                            if major < 3 or (major == 3 and minor < 5):
                                return m.group(0).replace(ver, "3.5")
                        except Exception:
                            return m.group(0).replace(ver, "3.5")
                        return m.group(0)
                    txt = re.sub(r"cmake_minimum_required\s*\(\s*VERSION\s+([0-9]+(?:\.[0-9]+)*)", _bump, txt, flags=re.IGNORECASE)
                    if txt != orig:
                        open(p, "w", encoding="utf-8").write(txt)
                        self.output.info(f"Patched cmake_minimum_required to 3.5 in {p}")
                except Exception as e:
                    self.output.warning(f"Failed to patch {p}: {e}")
        self._patch_tests_for_ctest()
        timer_h = os.path.join(self.source_folder, "test", "Timer.h")
        if os.path.exists(timer_h):
            try:
                orig = open(timer_h, encoding="utf-8", errors="ignore").read()
                if "rdtsc" in orig:
                    portable = '#pragma once\n\n#include <chrono>\n#include <stdint.h>\n#include <time.h>\n\n#ifdef __cplusplus\nextern "C" {\n#endif\n\ntypedef unsigned long long TimerType;\n\n#if defined(__x86_64__) || defined(__i386__) || defined(_M_IX86) || defined(_M_X64)\n#define CLOCK(ticks, ns) do { \\\n    volatile unsigned int a__, d__; \\\n    std::chrono::high_resolution_clock::duration dur__ = std::chrono::high_resolution_clock::now().time_since_epoch(); \\\n    ns = std::chrono::duration_cast<std::chrono::nanoseconds>(dur__).count(); \\\n    __asm__ __volatile__("rdtsc" : "=a" (a__), "=d" (d__) : ); \\\n    (ticks) = ((TimerType) a__)|(((TimerType)d__)<<32); \\\n  } while(0)\n#elif defined(__aarch64__) || defined(_M_ARM64) || defined(__ARM_ARCH)\nstatic inline uint64_t simint_aarch64_cntvct(void) { uint64_t v; __asm__ __volatile__("mrs %0, cntvct_el0" : "=r" (v)); return v; }\n#define CLOCK(ticks, ns) do { \\\n    std::chrono::high_resolution_clock::duration dur__ = std::chrono::high_resolution_clock::now().time_since_epoch(); \\\n    ns = std::chrono::duration_cast<std::chrono::nanoseconds>(dur__).count(); \\\n    (ticks) = simint_aarch64_cntvct(); \\\n  } while(0)\n#else\n#define CLOCK(ticks, ns) do { \\\n    std::chrono::high_resolution_clock::duration dur__ = std::chrono::high_resolution_clock::now().time_since_epoch(); \\\n    ns = std::chrono::duration_cast<std::chrono::nanoseconds>(dur__).count(); \\\n    (ticks) = (TimerType)ns; \\\n  } while(0)\n#endif\n\n#ifdef __cplusplus\n}\n#endif\n'
                    open(timer_h, "w", encoding="utf-8").write(portable)
                    self.output.info(f"Patched {timer_h} for aarch64 portable CLOCK (preserving TimerType)")
            except Exception as e:
                self.output.warning(f"Failed to patch Timer.h: {e}")
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build(cli_args=["-j1"])
        self._run_upstream_tests(cmake)

    def _run_upstream_tests(self, cmake):
        """Execute the upstream CTest suite and report counts from a single
        deterministic source (ctest output).  The 4 upstream test executables
        were registered with CTest by _patch_tests_for_ctest(), so ctest
        honestly discovers and runs them.  No counts are invented or repaired
        here: if ctest reports failures/zero the recipe reports honestly.
        """
        build_folder = self.build_folder
        ctest_output = ""
        discovered = 0
        executed = 0
        passed = 0
        failed = 0
        skipped = 0
        status = "failed"

        # 1) discovery: ctest -N is the single authoritative source for the
        #    registered total (upstream_test_total). One 'Test #N:' line per test.
        try:
            proc_n = subprocess.run(["ctest", "-N"], cwd=build_folder,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, timeout=120)
            out_n = proc_n.stdout or ""
            self.output.info(out_n.rstrip())
            for line in out_n.splitlines():
                if re.match(r"\s*Test\s+#\d+:", line):
                    discovered += 1
        except Exception as e:
            self.output.warning(f"ctest -N failed: {e}")

        # 2) execution: ctest --output-on-failure is the single authoritative
        #    source for executed/passed/failed/skipped (one 'Test #N ...' line
        #    per run test).
        try:
            proc = subprocess.run(["ctest", "--output-on-failure"], cwd=build_folder,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=900)
            ctest_output = proc.stdout or ""
            self.output.info(ctest_output.rstrip())
            # ctest per-test line format (normal verbosity), e.g.:
            #  1/4 Test #1: test_eri .......................   Passed    0.10 sec
            # executed counts only Passed/Failed (run-to-completion); Skipped is
            # tracked separately (per HMBS invariant: passed+failed==executed).
            for line in ctest_output.splitlines():
                m = re.search(r"Test\s+#\d+:\s+\S+.*?\b(Passed|Failed|Skipped)\b", line)
                if m:
                    res = m.group(1)
                    if res == "Passed":
                        executed += 1
                        passed += 1
                    elif res == "Failed":
                        executed += 1
                        failed += 1
                    elif res == "Skipped":
                        skipped += 1
        except Exception as e:
            self.output.warning(f"ctest execution failed: {e}")

        if executed > 0:
            status = "passed" if (failed == 0 and passed == executed) else "failed"
        else:
            # Nothing was executed. If tests were discovered but produced no
            # per-test lines we must not invent counts; report honestly.
            status = "no_tests" if discovered == 0 else "failed"

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
        ok = (
            discovered >= 0 and executed >= 0 and passed >= 0 and failed >= 0 and skipped >= 0
            and passed + failed == executed
            and executed <= discovered
            and skipped <= discovered
        )
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if not ok:
            raise RuntimeError(f"HMBS upstream test counts violate invariants: {upstream}")
        if status != "passed":
            tail = ctest_output[-2000:] if ctest_output else "(no ctest output)"
            raise RuntimeError(f"upstream tests not all passed: {upstream} tail: {tail}")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        for pattern in ["*.la", "*.dylib"]:
            try:
                rm(self, pattern, os.path.join(self.package_folder, "lib"))
            except Exception:
                pass

    def package_info(self):
        self.cpp_info.libs = ["simint"]
        self.cpp_info.set_property("cmake_file_name", "simint")
        self.cpp_info.set_property("cmake_target_name", "simint::simint")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
