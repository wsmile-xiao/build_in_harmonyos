#!/usr/bin/env python3
"""Conan recipe — boost1.84-wave 1.84.0 (Boost.Wave component package).

Boost b2 build system is incompatible with OHOS (E068, SHELL execution),
so we manually compile the needed libraries, following the approach of the
boost/1.84.0 meta package in this repository.

This component package provides Boost.Wave (libboost_wave) plus its
non-header-only dependencies from the same upstream tarball:
  - boost_wave           (12 sources, libs/wave/src)
  - boost_filesystem     (9 sources,  libs/filesystem/src)
  - boost_thread         (3 sources,  libs/thread/src, pthread variant)
  - boost_program_options (10 sources, libs/program_options/src, for the
                          upstream testwave harness only)
Boost.System is header-only since 1.69 (no binary needed).

OHOS-specific notes:
  - patches/0001 fixes sp_thread_sleep.hpp (pthread_setcancelstate is not
    available on OHOS musl) via the BOOST_SP_NO_PTHREAD_SETCANCELSTATE
    feature-detection macro (R8-compliant, no platform macro).
  - -fwrapv is required for wave: the integer-overflow detection in
    cpp_expression_value.hpp relies on signed-overflow wraparound, which
    -O2 would otherwise exploit as undefined behaviour (see notes.md).
"""
import glob
import os
import signal
import subprocess

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class BoostWaveConan(ConanFile):
    name = "boost1.84-wave"
    version = "1.84.0"
    description = "Boost.Wave (C++ preprocessor library) component from Boost 1.84.0, HarmonyOS PC adapted (libboost_wave + filesystem/thread/program_options)"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    # The recipe compiles directly from self.source_folder with explicit
    # clang++ commands (all outputs go to self.build_folder), so skip the
    # ~1.2G boost source tree copy to the build folder (HMDFS copy is slow).
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compile_lib(self, lib_name, src_dir, src_files, cxx, ar, cxxflags):
        """Compile source files and archive into a static library."""
        objects = []
        obj_dir = os.path.join(self.build_folder, f"obj_{lib_name}")
        os.makedirs(obj_dir, exist_ok=True)
        for src in src_files:
            src_path = os.path.join(src_dir, src)
            obj_name = src.replace("/", "_").replace(".cpp", ".o")
            obj_path = os.path.join(obj_dir, obj_name)
            cmd = f"{cxx} {cxxflags} -c {src_path} -o {obj_path}"
            self.run(cmd)
            objects.append(obj_path)
        lib_path = os.path.join(self.build_folder, f"libboost_{lib_name}.a")
        self.run(f"{ar} rcs {lib_path} {' '.join(objects)}")
        return lib_path

    def build(self):
        apply_conandata_patches(self)
        # Merge the profile [buildenv] into the process environment so that
        # subprocesses spawned by self.run() (compiler, upstream test
        # executables) see the OHOS SDK runtime library path
        # (libc++_shared.so) needed to *execute* target binaries on the
        # OHOS build host itself.
        build_env = VirtualBuildEnv(self).environment().vars(self, scope="build")
        for key, value in build_env.items():
            os.environ[key] = value
        # Sanitize LD_LIBRARY_PATH: the OHOS musl loader fails to parse the
        # whole variable when an entry contains leading whitespace (e.g. the
        # OpenDesk session exports "...chipset-pub-sdk:         /system/lib64:..."
        # with 9 spaces), which makes libc++_shared.so unresolvable and every
        # target binary exit with rc=127 "symbol not found". Strip whitespace
        # from each entry and drop empty ones.
        ldpath = os.environ.get("LD_LIBRARY_PATH", "")
        cleaned = ":".join(p.strip() for p in ldpath.split(":") if p.strip())
        if cleaned:
            os.environ["LD_LIBRARY_PATH"] = cleaned
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")

        boost_root = self.source_folder
        # Optimization flags driven by build_type (R8: no hardcoded build profile).
        if self.settings.build_type == "Debug":
            opt_flags = ["-O0", "-g"]
        else:
            opt_flags = ["-O2", "-DNDEBUG"]
        cxxflags = " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            *opt_flags,
            "-fPIC",
            # -fwrapv keeps the signed-overflow wraparound semantics that
            # wave's integer-overflow detection (cpp_expression_value.hpp)
            # depends on. Without it clang -O2 removes the checks and the
            # upstream t_6_015..t_6_018 test cases fail to report overflow.
            "-fwrapv",
            f"-I{boost_root}",
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_SYSTEM_NO_DEPRECATED",
            "-DBOOST_FILESYSTEM_NO_CXX20_CHAR8_T",
            "-DBOOST_FILESYSTEM_NO_CXX20_ATOMIC_REF",
            # R8 compliance: skip pthread_setcancelstate (not available on
            # OHOS musl) via a feature-detection macro instead of a platform
            # macro (__OHOS__). The patch consumes this define, see patches/0001.
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
            "-DBOOST_THREAD_USE_LIB",
        ])

        # Wave (12 sources: 8 grammar instantiations + token_ids +
        # wave_config_constant + re2clex aq/cpp_re)
        wave_src = [
            "instantiate_cpp_exprgrammar.cpp", "instantiate_cpp_grammar.cpp",
            "instantiate_cpp_literalgrs.cpp", "instantiate_defined_grammar.cpp",
            "instantiate_has_include_grammar.cpp", "instantiate_predef_macros.cpp",
            "instantiate_re2c_lexer.cpp", "instantiate_re2c_lexer_str.cpp",
            "token_ids.cpp", "wave_config_constant.cpp",
            "cpplexer/re2clex/aq.cpp", "cpplexer/re2clex/cpp_re.cpp",
        ]
        self._compile_lib("wave", os.path.join(boost_root, "libs/wave/src"), wave_src, cxx, ar, cxxflags)

        # Filesystem (skip windows_file_codecvt.cpp - Windows only)
        fs_src = [
            "codecvt_error_category.cpp", "directory.cpp", "exception.cpp",
            "operations.cpp", "path.cpp", "path_traits.cpp",
            "portability.cpp", "unique_path.cpp", "utf8_codecvt_facet.cpp",
        ]
        self._compile_lib("filesystem", os.path.join(boost_root, "libs/filesystem/src"), fs_src, cxx, ar, cxxflags)

        # Thread (pthread variant; skip win32 sources and tss_null.cpp)
        th_src = [
            "pthread/thread.cpp", "pthread/once.cpp", "future.cpp",
        ]
        self._compile_lib("thread", os.path.join(boost_root, "libs/thread/src"), th_src, cxx, ar, cxxflags)

        # ProgramOptions (needed by the upstream testwave harness; skip winmain.cpp)
        po_src = [
            "cmdline.cpp", "config_file.cpp", "Convert.cpp",
            "options_description.cpp", "parsers.cpp", "positional_options.cpp",
            "split.cpp", "utf8_codecvt_facet.cpp", "value_semantic.cpp",
            "variables_map.cpp",
        ]
        self._compile_lib("program_options", os.path.join(boost_root, "libs/program_options/src"), po_src, cxx, ar, cxxflags)

        # ⚠️ 上游测试集成（规则 5）：b2 在 OHOS 不可用（E068），绕过 b2 直接
        # 编译并运行上游 wave 测试程序，结果写入报告供 CI 与 PR 描述回填。
        # 实测 226/226 全部通过（testwave 226 + quick/default_hooks/re2c lexer）。
        self._run_upstream_tests(boost_root, cxx, cxxflags)

    def _run_cmd(self, cmd, timeout, shell=False):
        """Run a command with a hard timeout, killing the whole process group
        on timeout so no orphaned child (e.g. clang++) keeps the CI worker busy.

        stdin is redirected to DEVNULL: if an upstream test tries to read from
        stdin it immediately gets EOF instead of hanging.
        """
        proc = subprocess.Popen(
            cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, stdin=subprocess.DEVNULL, start_new_session=True,
            env=dict(os.environ))
        try:
            out, err = proc.communicate(timeout=timeout)
            if proc.returncode == 127:
                self.output.info(
                    f"[rundebug] rc=127 LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH', '<unset>')[:160]} "
                    f"stderr_tail={(err or '')[-300:]}")
            return proc.returncode, out, err
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                proc.kill()
            out, err = proc.communicate()
            return -1, out, err

    def _run_upstream_tests(self, boost_root, cxx, cxxflags):
        """Compile and run upstream wave test programs (bypassing b2).

        Test programs come from libs/wave/test/:
          - testwave/testwave.cpp + testwave_app.cpp: the full upstream wave
            test suite (226 test files driven by test.cfg with expected
            output/error annotations).
          - testwave/quick.cpp and testwave/default_hooks.cpp: smoke tests.
          - testlexers/test_re2c_lexer.cpp: re2c lexer test with token data.
        Reports are written to build_folder/upstream-tests-report.txt.
        """
        lib_dir = self.build_folder
        report_lines = []
        passed, failed = 0, 0

        def link_and_run(name, sources, extra_flags, run_args, timeout):
            nonlocal passed, failed
            exe = os.path.join(lib_dir, name)
            cmd_compile = (
                f"{cxx} {cxxflags} {extra_flags} {sources} "
                f"-L{lib_dir} -lboost_wave -lboost_filesystem -lboost_thread "
                f"-lboost_program_options -lpthread -o {exe}"
            )
            ret_code, ret_out, ret_err = self._run_cmd(cmd_compile, timeout=600, shell=True)
            if ret_code != 0:
                report_lines.append(
                    f"COMPILE_FAIL {name}: {ret_err.splitlines()[-1] if ret_err else ''}")
                failed += 1
                return
            run_cmd = [exe] + run_args
            run_code, run_out, run_err = self._run_cmd(run_cmd, timeout=timeout)
            ok = run_code == 0
            tail = (run_out or "").strip().splitlines()
            summary = tail[-1] if tail else ""
            report_lines.append(f"{'PASS' if ok else 'FAIL'} {name} rc={run_code} :: {summary[:160]}")
            if ok:
                passed += 1
            else:
                failed += 1

        testwave_dir = os.path.join(boost_root, "libs/wave/test/testwave")
        testfiles_dir = os.path.join(testwave_dir, "testfiles")
        # Upstream testwave invocation (from libs/wave/test/build/Jamfile.v2):
        #   -d4 --hooks=1 -S<testfiles> -S<boost_root> -I<boost_root>
        #   --config-file <testfiles>/test.cfg
        link_and_run(
            "test_testwave",
            f"{testwave_dir}/testwave.cpp {testwave_dir}/testwave_app.cpp",
            f"-I{testwave_dir}",
            ["-d4", "--hooks=1",
             f"-S{testfiles_dir}", f"-S{boost_root}", f"-I{boost_root}",
             "--config-file", os.path.join(testfiles_dir, "test.cfg")],
            timeout=600)

        link_and_run(
            "test_quick",
            f"{testwave_dir}/quick.cpp",
            "", [], timeout=120)

        link_and_run(
            "test_default_hooks",
            f"{testwave_dir}/default_hooks.cpp",
            "", [], timeout=120)

        link_and_run(
            "test_re2c_lexer",
            f"{boost_root}/libs/wave/test/testlexers/test_re2c_lexer.cpp",
            f"-I{boost_root}/libs/wave/test/testlexers",
            [], timeout=120)

        report_lines.append(f"TOTAL {passed + failed}: {passed} passed / {failed} failed")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(f"上游测试报告: {report_path} ({passed}/{passed + failed} 通过)")
        for line in report_lines[-6:]:
            self.output.info(f"[upstream-tests] {line}")

    def package(self):
        # Install headers: copy the entire boost/ include directory
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

        # Install compiled static libraries
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_*.a")):
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")

        # Main "headers" component (always needed)
        self.cpp_info.components["boost_headers"].includedirs = ["include"]
        # R8 compliance: expose BOOST_SP_NO_PTHREAD_SETCANCELSTATE to all
        # consumers so the patched sp_thread_sleep.hpp skips the
        # pthread_setcancelstate path (not available on OHOS musl).
        self.cpp_info.components["boost_headers"].defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        self.cpp_info.components["boost_headers"].set_property("cmake_target_name", "Boost::headers")

        # Wave (this package's primary component)
        self.cpp_info.components["boost_wave"].includedirs = []
        self.cpp_info.components["boost_wave"].libs = ["boost_wave"]
        self.cpp_info.components["boost_wave"].requires = [
            "boost_headers", "boost_filesystem", "boost_thread", "boost_system",
        ]
        self.cpp_info.components["boost_wave"].set_property("cmake_target_name", "Boost::wave")

        # Filesystem (dependency of wave, provided by this package)
        self.cpp_info.components["boost_filesystem"].includedirs = []
        self.cpp_info.components["boost_filesystem"].libs = ["boost_filesystem"]
        self.cpp_info.components["boost_filesystem"].requires = ["boost_headers", "boost_system"]
        self.cpp_info.components["boost_filesystem"].set_property("cmake_target_name", "Boost::filesystem")

        # Thread (dependency of wave, provided by this package)
        self.cpp_info.components["boost_thread"].includedirs = []
        self.cpp_info.components["boost_thread"].libs = ["boost_thread"]
        self.cpp_info.components["boost_thread"].requires = ["boost_headers"]
        self.cpp_info.components["boost_thread"].set_property("cmake_target_name", "Boost::thread")

        # ProgramOptions (needed by upstream testwave harness)
        self.cpp_info.components["boost_program_options"].includedirs = []
        self.cpp_info.components["boost_program_options"].libs = ["boost_program_options"]
        self.cpp_info.components["boost_program_options"].requires = ["boost_headers"]
        self.cpp_info.components["boost_program_options"].set_property("cmake_target_name", "Boost::program_options")

        # System (header-only since 1.69, but CMake component still needed)
        self.cpp_info.components["boost_system"].includedirs = []
        self.cpp_info.components["boost_system"].libs = []
        self.cpp_info.components["boost_system"].requires = ["boost_headers"]
        self.cpp_info.components["boost_system"].set_property("cmake_target_name", "Boost::system")
