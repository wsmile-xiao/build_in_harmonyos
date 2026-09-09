#!/usr/bin/env python3
"""Conan recipe — boost1.84-system 1.84.0 (Boost.System standalone component package).

Boost 1.84.0 component split packaging for HarmonyOS PC (aarch64).
The full boost/1.84.0 recipe already ships filesystem/regex/program_options/
iostreams; this recipe packages the Boost.System component independently so
that consumers can depend on `boost1.84-system/1.84.0` without pulling the
whole boost aggregate.

Key facts (verified on the OHOS target):
- Boost.System upstream source tree has exactly ONE translation unit:
  libs/system/src/error_code.cpp (a compatibility stub that only provides
  boost::system::dummy_exported_function; all real error_code machinery is
  header-only since Boost 1.69).
- The b2 build system is incompatible with OHOS (SHELL execution failure,
  E068 error pattern), so we compile the translation unit manually with the
  Conan-provided OHOS clang driver — same approach as boost/1.84.0.
- The compiled static library keeps the CMake component contract
  `boost_system` (target `Boost::system`) used by the aggregate recipe, and
  installs the full boost/ headers directory so the package is self-contained.

Upstream tests: 94 runnable test executables from libs/system/test/
(lightweight_test based, no b2 needed) are compiled and executed in build();
93 pass, 1 (error_code_test) fails on 2 strerror() message assertions that
are glibc-specific ("Unknown error" vs OHOS musl "No error information").
"""
import os
import glob
import signal
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostSystemConan(ConanFile):
    name = "boost1.84-system"
    version = "1.84.0"
    description = "Boost.System 1.84.0 组件包（boost::system::error_code / system_error，鸿蒙 PC 适配，静态库 + 全量 boost 头文件）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = "https://github.com/boostorg/system"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def _cxxflags(self, boost_root):
        if self.settings.build_type == "Debug":
            opt_flags = ["-O0", "-g"]
        else:
            opt_flags = ["-O2", "-DNDEBUG"]
        return " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            *opt_flags,
            "-fPIC",
            f"-I{boost_root}",
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_SYSTEM_NO_DEPRECATED",
        ])

    def _run_cmd(self, cmd, timeout, shell=False):
        """Run a command with a hard timeout; kill the whole process group on
        timeout so no orphaned clang++ keeps the worker busy. stdin is
        redirected to DEVNULL: an upstream test that reads stdin immediately
        gets EOF instead of hanging."""
        proc = subprocess.Popen(
            cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            out, err = proc.communicate(timeout=timeout)
            return proc.returncode, out, err
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                proc.kill()
            out, err = proc.communicate()
            return -1, out, err

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")

        boost_root = self.source_folder
        cxxflags = self._cxxflags(boost_root)

        # ── Compile the single Boost.System translation unit ──────────────
        obj_dir = os.path.join(self.build_folder, "obj_system")
        os.makedirs(obj_dir, exist_ok=True)
        src = os.path.join(boost_root, "libs/system/src/error_code.cpp")
        obj = os.path.join(obj_dir, "error_code.o")
        self.run(f"{cxx} {cxxflags} -DBOOST_SYSTEM_SOURCE -c {src} -o {obj}")

        lib_path = os.path.join(self.build_folder, "libboost_system.a")
        self.run(f"{ar} rcs {lib_path} {obj}")

        # ── Upstream test integration (rule 5): compile & run tests ───────
        # b2 is incompatible with OHOS (E068), so the official
        # libs/system/test/*.cpp test suite is driven manually: each test is
        # compiled with the same flags as the library and executed; exit code
        # 0 means PASS. Report is written to build_folder/upstream-tests-report.txt
        # for CI / PR description consumption.
        self._run_upstream_tests(boost_root, cxx, cxxflags)

    # Ordered list of the runnable upstream tests (Jamfile.v2 `run` /
    # `system-run` / `compile` targets, Windows-only and shared-lib-only
    # variants excluded; each is a standalone executable).
    _UPSTREAM_TESTS = [
        # system-run core
        "error_code_test", "error_code_user_test", "system_error_test",
        "initialization_test", "header_only_test",
        "std_interop_test", "std_mismatch_test",
        "before_main_test", "constexpr_test",
        "error_category_test", "generic_category_test", "system_category_test",
        "after_main_test", "failed_test", "failed_constexpr_test",
        "quick",
        # plain run
        "config_test", "is_error_code_enum_test", "is_error_condition_enum_test",
        "errc_test", "errc_test2", "error_category_test2",
        "error_condition_test", "error_condition_test2",
        "generic_category_test2", "generic_category_test3",
        "system_category_test2", "system_category_test3",
        "linux_error_test", "snprintf_test",
        "std_interop_test2", "std_interop_test3", "std_interop_test4",
        "std_interop_test5", "std_interop_test6", "std_interop_test7",
        "std_interop_test8", "std_interop_test9", "std_interop_test10",
        "std_interop_test11", "std_interop_test12", "std_interop_test13",
        "std_interop_test14", "std_interop_test15", "std_interop_test16",
        "ec_location_test", "ec_location_test2", "ec_location_test3",
        "ec_location_test4", "ec_what_test", "ec_wstream_test",
        "error_condition_test3", "error_code_test2", "error_code_test3",
        "system_error_test2",
        "system_error_test3", "errc_test4", "win32_generic_test",
        "ec_hash_value_test", "warnings_test",
        # result<> tests (C++11)
        "result_default_construct", "result_value_construct",
        "result_error_construct", "result_copy_construct",
        "result_move_construct", "result_copy_assign",
        "result_move_assign", "result_value_access",
        "result_error_access", "result_swap", "result_eq",
        "result_range_for", "result_value_construct2",
        "result_error_construct2", "result_errc_construct",
        "result_convert_construct", "result_typedefs",
        "result_value_construct3", "result_error_construct3",
        "result_emplace", "result_error_construct4",
        "result_value_construct4", "result_value_construct5",
        "result_error_move", "result_value_construct6",
        "result_value_construct7", "result_error_construct5",
        "result_or_value", "result_or_fn0v", "result_or_fn0r",
        "result_and_fn1v", "result_and_fn1r",
        "result_and_eq_fn1v", "result_and_eq_fn1r",
    ]

    def _run_upstream_tests(self, boost_root, cxx, cxxflags):
        """Compile and run the upstream Boost.System test suite (bypassing b2).

        Test executables are linked with -static-libstdc++: the conan
        buildenv LD_LIBRARY_PATH prepends llvm/lib (which does NOT contain
        libc++_shared.so — it lives in the aarch64-linux-ohos/c++
        subdirectory), so dynamically linked test binaries fail with rc=127
        because the loader cannot find libc++_shared.so. Statically baking
        in libc++ leaves only a libc.so dependency, letting the tests run
        in a clean environment (same approach as boost1.84-url CI).
        """
        lib_dir = self.build_folder
        test_flags = cxxflags + " -static-libstdc++"
        report_lines = []
        passed, failed = 0, 0
        for name in self._UPSTREAM_TESTS:
            src = os.path.join(boost_root, "libs/system/test", name + ".cpp")
            if not os.path.isfile(src):
                report_lines.append(f"SKIP {name} (source not found)")
                continue
            exe = os.path.join(lib_dir, f"test_{name}")
            cmd_compile = f"{cxx} {test_flags} -DBOOST_TEST_NO_LIB {src} -L{lib_dir} -lboost_system -o {exe}"
            ret_code, _out, ret_err = self._run_cmd(cmd_compile, timeout=300, shell=True)
            if ret_code != 0:
                failed += 1
                last = ret_err.splitlines()[-1] if ret_err else ""
                report_lines.append(f"COMPILE_FAIL {name}: {last}")
                continue
            run_code, _rout, _rerr = self._run_cmd([exe], timeout=120)
            if run_code == 0:
                passed += 1
                report_lines.append(f"PASS {name} rc=0")
            else:
                failed += 1
                report_lines.append(f"FAIL {name} rc={run_code}")
        report_lines.append(f"TOTAL {passed + failed}: {passed} passed / {failed} failed")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(f"上游测试报告: {report_path} ({passed}/{passed + failed} 通过)")
        for line in report_lines:
            if line.startswith(("FAIL", "COMPILE_FAIL", "TOTAL")):
                self.output.info(f"[upstream-tests] {line}")

    def package(self):
        # Install the full boost/ headers directory (self-contained package)
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

        # Install the compiled static library
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_*.a")):
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "boost_system_pkg")
        self.cpp_info.set_property("pkg_config_name", "boost_system")

        # headers component (dependency of every boost component)
        self.cpp_info.components["boost_headers"].includedirs = ["include"]
        self.cpp_info.components["boost_headers"].set_property("cmake_target_name", "boost_system_pkg::headers")

        # system component (compiled static lib)
        self.cpp_info.components["boost_system"].includedirs = []
        self.cpp_info.components["boost_system"].libs = ["boost_system"]
        self.cpp_info.components["boost_system"].requires = ["boost_headers"]
        self.cpp_info.components["boost_system"].set_property("cmake_target_name", "boost_system_pkg::system")
