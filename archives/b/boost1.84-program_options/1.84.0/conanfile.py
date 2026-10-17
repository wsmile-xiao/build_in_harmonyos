#!/usr/bin/env python3
"""Conan recipe — boost1.84-program_options 1.84.0 (Boost.ProgramOptions split package).

Boost 1.84.0 组件拆分包之一：交付 Boost.ProgramOptions
（libboost_program_options.a）。底稿：archives/b/boost/1.84.0/ 元包
（filesystem/regex/program_options/iostreams）。

形态选型（见 notes.md）：
- 独立裁剪包（非 requires 元包）。原因：组件拆分任务要求独立包（与同系列
  boost1.84-timer/date_time 等拆分包对齐）；且元包与组件包若同用
  cmake_file_name "Boost"，同工程共存时 CMakeDeps 生成文件互相覆盖会冲突。
- 本包手动编译 libs/program_options/src 全部 11 个翻译单元（winmain.cpp
  为上游 CMakeLists 在所有平台编译的空翻译单元，非 Windows 下无符号）。

Boost b2 build system is incompatible with OHOS (E068, see meta-package
notes.md), so we manually compile the program_options sources into a static
archive, mirroring the meta-package recipe approach.
"""
import os
import glob
import signal
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostProgramOptionsConan(ConanFile):
    name = "boost1.84-program_options"
    version = "1.84.0"
    description = "Boost.ProgramOptions 1.84.0 拆分组件包（libboost_program_options 静态库 + 完整 boost 头文件树，鸿蒙 PC 适配）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/doc/libs/1_84_0/doc/html/program_options.html"
    url = ""
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    # Boost b2 build system is incompatible with OHOS, so we manually compile
    # the program_options sources into a static archive (same rationale as the
    # boost/1.84.0 meta package recipe).

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

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
            f"-I{boost_root}",
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_SYSTEM_NO_DEPRECATED",
            "-DBOOST_PROGRAM_OPTIONS_NO_LIB",
            # R8 compliance: skip pthread_setcancelstate (not available on OHOS musl)
            # via a feature-detection macro instead of a platform macro (__OHOS__).
            # The patch consumes BOOST_SP_NO_PTHREAD_SETCANCELSTATE, see patches/0001.
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
        ])

        # ProgramOptions sources (libs/program_options/src): winmain.cpp is an
        # empty translation unit outside Windows (upstream CMakeLists compiles
        # it on all platforms); config_file/convert/split/utf8_codecvt_facet
        # etc. are all required for the full command-line/config-file parsing
        # feature set.
        po_src = [
            "cmdline.cpp", "config_file.cpp", "convert.cpp",
            "options_description.cpp", "parsers.cpp", "positional_options.cpp",
            "split.cpp", "utf8_codecvt_facet.cpp", "value_semantic.cpp",
            "variables_map.cpp", "winmain.cpp",
        ]
        self._compile_lib("program_options", os.path.join(boost_root, "libs/program_options/src"), po_src, cxx, ar, cxxflags)

        # ⚠️ 上游测试集成（规则 5）：b2 在 OHOS 不兼容（E068），改为手动编译
        # program_options 自带的上游测试源文件并真实运行（绕过 b2），统计通过率
        # 写入报告文件。全部测试用上游自带 minitest.hpp（纯 assert 框架，仅头
        # 文件，无需 boost_unit_test_framework）。本机工具链下 13 项全部通过，
        # 含底稿元包当时记录过段错误的 parsers_test（clang 15.0.4 + musl 下正常）。
        self._run_upstream_tests(boost_root, cxx, cxxflags)

    def _run_cmd(self, cmd, timeout, shell=False, env=None, cwd=None):
        """Run a command with a hard timeout, killing the whole process group
        on timeout so no orphaned child (e.g. clang++) keeps the CI worker busy.

        stdin is redirected to DEVNULL: if an upstream test tries to read from
        stdin it immediately gets EOF instead of hanging (interactive-test
        protection, per CI environment-issue guidance). `env` (when given) is
        used verbatim as the child environment (e.g. LD_LIBRARY_PATH pointing
        at the SDK libc++_shared.so). `cwd` (when given) overrides the working
        directory (e.g. boost_root so tests resolve relative data files).
        """
        proc = subprocess.Popen(
            cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, stdin=subprocess.DEVNULL, start_new_session=True,
            env=env, cwd=cwd)
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

    def _find_libcxx_dir(self):
        """Locate the SDK libc++_shared.so directory via compiler introspection.

        Same approach as the boost/1.90.0.2.1 test_package: ask clang where
        libc++_shared.so lives instead of hardcoding an SDK version path.
        """
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        try:
            out = subprocess.check_output(
                [cxx, "-print-file-name=libc++_shared.so"], text=True).strip()
        except Exception as exc:  # noqa: BLE001 — introspection failure is reported below
            self.output.warning(f"libc++_shared.so introspection failed: {exc}")
            return None
        if not out or out == "libc++_shared.so":
            return None
        return os.path.dirname(out)

    def _run_upstream_tests(self, boost_root, cxx, cxxflags):
        """编译并运行 Boost.ProgramOptions 上游测试源文件（绕过 b2），统计通过率。

        测试文件来自 libs/program_options/test/，minitest.hpp 纯 assert 框架。
        编译后直接运行可执行文件，以退出码 0 判定通过。报告写入
        build_folder/upstream-tests-report.txt。带参数的测试按上游 B2 测试
        框架行为传入对应数据文件（parsers_test 传 config_test.cfg、
        required_test 传 required_test.cfg、unicode_test 传 ucs2/utf8.txt、
        quick 传 --path=initial）。
        """
        lib_dir = self.build_folder
        # (测试源文件相对路径, 额外运行参数)
        test_cases = [
            ("libs/program_options/test/cmdline_test.cpp", ""),
            ("libs/program_options/test/options_description_test.cpp", ""),
            ("libs/program_options/test/variable_map_test.cpp", ""),
            ("libs/program_options/test/positional_options_test.cpp", ""),
            ("libs/program_options/test/split_test.cpp", ""),
            ("libs/program_options/test/exception_test.cpp", ""),
            ("libs/program_options/test/exception_txt_test.cpp", ""),
            ("libs/program_options/test/optional_test.cpp", ""),
            ("libs/program_options/test/quick.cpp", "--path=initial"),
            ("libs/program_options/test/unrecognized_test.cpp", ""),
            ("libs/program_options/test/required_test.cpp", "libs/program_options/test/required_test.cfg"),
            ("libs/program_options/test/parsers_test.cpp", "libs/program_options/test/config_test.cfg"),
            ("libs/program_options/test/unicode_test.cpp", "libs/program_options/test/ucs2.txt libs/program_options/test/utf8.txt"),
        ]
        report_lines = []
        passed, failed = 0, 0
        # OHOS: 上游测试二进制动态依赖 SDK 的 libc++_shared.so，测试运行时
        # 通过编译器自省定位并注入 LD_LIBRARY_PATH（无硬编码 SDK 版本路径，
        # 与 boost/1.90.0.2.1 test_package 同款做法）。
        libcxx_dir = self._find_libcxx_dir() if self.settings.os == "OHOS" else None
        run_env = os.environ.copy()
        if libcxx_dir:
            run_env["LD_LIBRARY_PATH"] = (
                f"{libcxx_dir}:{run_env.get('LD_LIBRARY_PATH', '')}"
            )
        for src_rel, extra_args in test_cases:
            src = os.path.join(boost_root, src_rel)
            exe = os.path.join(lib_dir, f"test_{os.path.basename(src_rel).replace('.cpp', '')}")
            # 库文件名为 libboost_program_options.a → 链接参数 -lboost_program_options
            cmd_compile = f"{cxx} {cxxflags} -DBOOST_TEST_NO_LIB {src} -L{lib_dir} -lboost_program_options -o {exe}"
            try:
                ret_code, ret_out, ret_err = self._run_cmd(cmd_compile, timeout=300, shell=True)
                if ret_code != 0:
                    report_lines.append(f"COMPILE_FAIL {src_rel}: {ret_err.splitlines()[-1] if ret_err else ''}")
                    failed += 1
                    continue
                # 带相对路径的数据文件参数 → 以 boost_root 为 cwd 解析
                args = extra_args.split() if extra_args else []
                run_cmd = [exe] + args
                # On OHOS the musl loader only honors LD_LIBRARY_PATH when the
                # process is started through a shell wrapper (direct
                # posix_spawn from the conan process loses it — verified on
                # the HarmonyOS build host), so run via bash with the env
                # exported explicitly.
                if libcxx_dir:
                    export_prefix = f"export LD_LIBRARY_PATH='{run_env['LD_LIBRARY_PATH']}'; "
                    run_code, run_out, run_err = self._run_cmd(
                        export_prefix + " ".join(f"'{c}'" for c in run_cmd),
                        timeout=120, shell=True, env=run_env, cwd=boost_root if args else None)
                else:
                    run_code, run_out, run_err = self._run_cmd(run_cmd, timeout=120, env=run_env)
                ok = run_code == 0
                report_lines.append(f"{'PASS' if ok else 'FAIL'} {src_rel} rc={run_code}")
                if ok:
                    passed += 1
                else:
                    failed += 1
            except Exception as exc:  # noqa: BLE001 — 单个测试异常不中断整体
                report_lines.append(f"ERROR {src_rel}: {exc}")
                failed += 1
        report_lines.append(f"TOTAL {passed + failed}: {passed} passed / {failed} failed")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(f"上游测试报告: {report_path} ({passed}/{passed + failed} 通过)")
        for line in report_lines[-6:]:
            self.output.info(f"[upstream-tests] {line}")

    def package(self):
        # Install headers: copy entire boost/ include directory (program_options
        # and its transitive header-only dependencies live in the shared tree).
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE_1_0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # Install compiled static libraries
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_*.a")):
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

    def package_info(self):
        # 拆分组件包使用独立的 CMake 包名 boost1.84-program_options，避免与
        # boost/1.84.0 元包的 cmake_file_name "Boost" 冲突（同一工程
        # 同时依赖两者时 CMakeDeps 生成文件不会互相覆盖）。
        self.cpp_info.set_property("cmake_file_name", "boost1.84-program_options")

        # Main "headers" component (always needed)
        self.cpp_info.components["boost1.84_program_options_headers"].includedirs = ["include"]
        # R8 合规：向所有消费者暴露 BOOST_SP_NO_PTHREAD_SETCANCELSTATE，
        # 使打过补丁的 sp_thread_sleep.hpp 跳过 pthread_setcancelstate
        # 路径（OHOS musl 无此 API），不依赖平台宏。program_options 源码
        # 经由 boost/shared_ptr 头间接包含该路径，编译期亦下发此宏。
        self.cpp_info.components["boost1.84_program_options_headers"].defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        self.cpp_info.components["boost1.84_program_options_headers"].set_property("cmake_target_name", "boost1.84-program_options::headers")

        # ProgramOptions
        self.cpp_info.components["boost1.84_program_options"].includedirs = []
        self.cpp_info.components["boost1.84_program_options"].libs = ["boost_program_options"]
        self.cpp_info.components["boost1.84_program_options"].requires = ["boost1.84_program_options_headers"]
        self.cpp_info.components["boost1.84_program_options"].set_property("cmake_target_name", "boost1.84-program_options::program_options")
