#!/usr/bin/env python3
"""Conan recipe — boost1.90 1.90.0 (manual compilation of select libraries).

Boost b2 build system is incompatible with OHOS (E068), so we manually compile
the needed non-header-only libraries: filesystem, regex, program_options,
iostreams. System is header-only since Boost 1.69.
Compared with boost1.84 1.84.0 (recipe sibling): Boost 1.90 regex is trimmed
to 2 source files (posix_api/wide_posix_api, ICU-independent build), and
upstream now guards pthread_setcancelstate with __OHOS__ natively (no patch
needed). The sp_thread_sleep fix patch of boost1.84 is therefore dropped.
"""
import glob
import os
import signal
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Boost190Conan(ConanFile):
    name = "boost1.90"
    version = "1.90.0"
    description = "Boost C++ Libraries 1.90.0（手动编译 4 个库：filesystem/regex/program_options/iostreams，鸿蒙 PC 适配；boost1.90 为独立包名归档，与 boost/1.90.0 header-only 并行维护）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = "https://www.boost.org/"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    # Boost b2 build system is incompatible with OHOS, so we manually compile
    # select non-header-only libraries into static archives. Dynamic library
    # building would require b2 (which fails on OHOS), so the recipe only
    # produces static libraries — see notes.md for the rationale.

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

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
            "-DBOOST_FILESYSTEM_NO_CXX20_CHAR8_T",
            "-DBOOST_FILESYSTEM_NO_CXX20_ATOMIC_REF",
            "-DBOOST_IOSTREAMS_NO_LIB",
            f"-I{os.path.join(self.dependencies['zlib'].package_folder, 'include')}",
        ])

        # Filesystem: skip windows_file_codecvt.cpp (Windows only)
        fs_src = [
            "codecvt_error_category.cpp", "directory.cpp", "exception.cpp",
            "operations.cpp", "path.cpp", "path_traits.cpp",
            "portability.cpp", "unique_path.cpp", "utf8_codecvt_facet.cpp",
        ]
        self._compile_lib("filesystem", os.path.join(boost_root, "libs/filesystem/src"), fs_src, cxx, ar, cxxflags)

        # Regex: Boost 1.90 trimmed the compiled sources to the two
        # ICU-independent API wrappers (libs/regex/build/Jamfile.v2 SOURCES).
        re_src = [
            "posix_api.cpp", "wide_posix_api.cpp",
        ]
        self._compile_lib("regex", os.path.join(boost_root, "libs/regex/src"), re_src, cxx, ar, cxxflags)

        # ProgramOptions: skip winmain.cpp (Windows only)
        po_src = [
            "cmdline.cpp", "config_file.cpp", "convert.cpp",
            "options_description.cpp", "parsers.cpp", "positional_options.cpp",
            "split.cpp", "utf8_codecvt_facet.cpp", "value_semantic.cpp",
            "variables_map.cpp",
        ]
        self._compile_lib("program_options", os.path.join(boost_root, "libs/program_options/src"), po_src, cxx, ar, cxxflags)

        # Iostreams: compile the core files + zlib (skip bzip2/lzma/zstd - no system libs)
        io_src = [
            "file_descriptor.cpp", "gzip.cpp", "mapped_file.cpp", "zlib.cpp",
        ]
        self._compile_lib("iostreams", os.path.join(boost_root, "libs/iostreams/src"), io_src, cxx, ar, cxxflags)

        # Boost.Test unit_test_framework: needed to run upstream iostreams tests
        # (their test-iostreams rule links /boost/test//boost_unit_test_framework
        # statically). Built from the upstream official BOOST_UTF_SRC list in
        # libs/test/build/CMakeLists.txt (19 translation units).
        ut_src = [
            "compiler_log_formatter", "debug", "decorator",
            "execution_monitor", "framework", "junit_log_formatter",
            "plain_report_formatter", "progress_monitor", "results_collector",
            "results_reporter", "test_framework_init_observer", "test_tools",
            "test_tree", "unit_test_log", "unit_test_main", "unit_test_monitor",
            "unit_test_parameters", "xml_log_formatter", "xml_report_formatter",
        ]
        ut_flags = cxxflags + f" -I{os.path.join(boost_root, 'libs', 'test', 'include')}"
        self._compile_lib("unit_test_framework", os.path.join(boost_root, "libs/test/src"),
                          [s + ".cpp" for s in ut_src], cxx, ar, ut_flags)

        # ⚠️ 上游测试集成（规则 5）：b2 构建系统在 OHOS 不兼容（SHELL 执行机制
        # 失败，E068 错误模式），无法直接运行 B2 测试目标。这里改为手动编译各库
        # 自带的测试源文件（绕过 b2）并真实运行，统计通过率写入报告文件供 CI
        # 与 PR 描述回填。测试选择以各库 test/Jamfile.v2 注册的规则为准。
        self._run_upstream_tests(boost_root, cxx, cxxflags)

    def _run_cmd(self, cmd, timeout, shell=False, cwd=None, env=None):
        """Run a command with a hard timeout, killing the whole process group
        on timeout so no orphaned child (e.g. clang++) keeps the CI worker busy.

        stdin is redirected to DEVNULL: if an upstream test tries to read from
        stdin it immediately gets EOF instead of hanging (interactive-test
        protection, per CI environment-issue guidance).
        """
        proc = subprocess.Popen(
            cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, stdin=subprocess.DEVNULL, cwd=cwd, env=env,
            start_new_session=True)
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

    def _run_upstream_tests(self, boost_root, cxx, cxxflags):
        """编译并运行已编译库的上游测试源文件（绕过 b2），统计通过率。

        测试文件取自 boost 1.90.0 各库 libs/<lib>/test/，以各库 test/Jamfile.v2
        注册的 run 规则为准（上游构建系统注册的测试目标），编译后直接运行
        可执行文件，以退出码 0 判定通过。报告写入 build_folder/upstream-tests-report.txt。

        iostreams 系列测试依赖 boost_unit_test_framework 静态库（上游
        test-iostreams 规则显式链接 /boost/test//boost_unit_test_framework），
        本配方已在 build() 中编译该库（归档为 libboost_unit_test_framework.a）。
        """
        lib_dir = self.build_folder
        # (库, 测试源文件相对路径, 链接库, 额外编译宏, 额外运行参数)
        # 选择范围：各库 test/Jamfile.v2 注册且不依赖 Windows 专有机制、
        # 不需要 ICU 的 run 目标。每库覆盖核心 run 规则 + quick 目标。
        test_cases = [
            # filesystem (Jamfile 注册 34 目标: 主 32 + issues/ 2)：
            # 取 v4 默认口径的代表性 run 目标 + quick
            ("filesystem", "libs/filesystem/test/copy_test.cpp", ["boost_filesystem"], "", ""),
            ("filesystem", "libs/filesystem/test/convenience_test.cpp", ["boost_filesystem"], "-DBOOST_FILESYSTEM_VERSION=4", ""),
            ("filesystem", "libs/filesystem/test/foreach_test.cpp", ["boost_filesystem"], "-DBOOST_FILESYSTEM_VERSION=4", ""),
            ("filesystem", "libs/filesystem/test/large_file_support_test.cpp", ["boost_filesystem"], "-DBOOST_FILESYSTEM_VERSION=4", ""),
            ("filesystem", "libs/filesystem/test/path_test.cpp", ["boost_filesystem"], "-DBOOST_FILESYSTEM_VERSION=4", ""),
            ("filesystem", "libs/filesystem/test/path_unit_test.cpp", ["boost_filesystem"], "-DBOOST_FILESYSTEM_VERSION=4", ""),
            ("filesystem", "libs/filesystem/test/relative_test.cpp", ["boost_filesystem"], "-DBOOST_FILESYSTEM_VERSION=4", ""),
            ("filesystem", "libs/filesystem/test/quick.cpp", ["boost_filesystem"], "-DBOOST_FILESYSTEM_VERSION=4", ""),
            # regex (Jamfile 注册 37 目标)：quick + issue 系列（ICU 无关）
            ("regex", "libs/regex/test/quick.cpp", ["boost_regex"], "", ""),
            ("regex", "libs/regex/test/issue153.cpp", ["boost_regex"], "", ""),
            ("regex", "libs/regex/test/issue227.cpp", ["boost_regex"], "", ""),
            ("regex", "libs/regex/test/issue232.cpp", ["boost_regex"], "", ""),
            ("regex", "libs/regex/test/issue244.cpp", ["boost_regex"], "", ""),
            ("regex", "libs/regex/test/issue245.cpp", ["boost_regex"], "", ""),
            # program_options (Jamfile 注册 30 目标: 14 po-test x2 + rtti-off + quick)
            ("program_options", "libs/program_options/test/cmdline_test.cpp", ["boost_program_options"], "", ""),
            ("program_options", "libs/program_options/test/exception_test.cpp", ["boost_program_options"], "", ""),
            ("program_options", "libs/program_options/test/exception_txt_test.cpp", ["boost_program_options"], "", ""),
            ("program_options", "libs/program_options/test/optional_test.cpp", ["boost_program_options"], "", ""),
            ("program_options", "libs/program_options/test/options_description_test.cpp", ["boost_program_options"], "", ""),
            ("program_options", "libs/program_options/test/parsers_test.cpp", ["boost_program_options"], "", ""),
            ("program_options", "libs/program_options/test/positional_options_test.cpp", ["boost_program_options"], "", ""),
            ("program_options", "libs/program_options/test/quick.cpp", ["boost_program_options"], "", "--path=initial"),
            ("program_options", "libs/program_options/test/split_test.cpp", ["boost_program_options"], "", ""),
            ("program_options", "libs/program_options/test/required_test.cpp", ["boost_program_options"], "", "required_test.cfg"),
            ("program_options", "libs/program_options/test/unrecognized_test.cpp", ["boost_program_options"], "", ""),
            ("program_options", "libs/program_options/test/variable_map_test.cpp", ["boost_program_options"], "", ""),
            # iostreams (Jamfile 注册 45 目标)：unit_test_framework 驱动，zlib 后端
            ("iostreams", "libs/iostreams/test/gzip_test.cpp", ["boost_iostreams", "boost_unit_test_framework", "boost_filesystem"], "", ""),
            ("iostreams", "libs/iostreams/test/file_test.cpp", ["boost_iostreams", "boost_unit_test_framework", "boost_filesystem"], "", ""),
            ("iostreams", "libs/iostreams/test/filtering_stream_test.cpp", ["boost_iostreams", "boost_unit_test_framework", "boost_filesystem"], "", ""),
            ("iostreams", "libs/iostreams/test/mapped_file_test.cpp", ["boost_iostreams", "boost_unit_test_framework", "boost_filesystem"], "", ""),
            ("iostreams", "libs/iostreams/test/file_descriptor_test.cpp", ["boost_iostreams", "boost_unit_test_framework", "boost_filesystem"], "", ""),
            ("iostreams", "libs/iostreams/test/copy_test.cpp", ["boost_iostreams", "boost_unit_test_framework", "boost_filesystem"], "", ""),
        ]
        report_lines = []
        passed, failed = 0, 0
        for lib, src_rel, link_libs, extra_defs, extra_args in test_cases:
            src = os.path.join(boost_root, src_rel)
            if not os.path.isfile(src):
                report_lines.append(f"MISSING {src_rel}")
                failed += 1
                continue
            exe = os.path.join(lib_dir, f"test_{os.path.basename(src_rel).replace('.cpp', '')}")
            lib_args = " ".join(f"-l{l}" for l in link_libs)
            run_dir = os.path.dirname(src)
            # zlib 库路径：iostreams 测试的 gzip 后端链接 zlib 符号
            zlib_libdir = os.path.join(
                self.dependencies["zlib"].package_folder, "lib")
            cmd_compile = (
                f"{cxx} {cxxflags} {extra_defs} -DBOOST_TEST_NO_LIB "
                f"{src} -L{lib_dir} {lib_args} -L{zlib_libdir} -lz -o {exe}"
            )
            # iostreams/program_options 部分测试需要其所在目录的辅助文件
            # （required_test.cfg 等），运行时切到测试源目录。
            try:
                ret_code, ret_out, ret_err = self._run_cmd(cmd_compile, timeout=600, shell=True)
                if ret_code != 0:
                    last_err = ret_err.splitlines()[-1] if ret_err else ""
                    report_lines.append(f"COMPILE_FAIL {src_rel}: {last_err}")
                    failed += 1
                    continue
                run_cmd = [os.path.abspath(exe)] + (extra_args.split() if extra_args else [])
                # 交叉编译产物运行：OHOS 设备上系统自带 libc++_shared.so；
                # 在构建机（同为 OHOS aarch64）上运行时通过 LD_LIBRARY_PATH
                # 兜底指向 toolchain 的 libc++ 目录。
                import copy as _copy
                run_env = _copy.deepcopy(dict(os.environ))
                # OHOS 设备的系统 libc++_shared.so 可能旧于 toolchain（缺
                # __on_zero_shared 等新符号，rc=127），需优先加载 toolchain 的
                # libc++。从编译器路径向上探测 llvm/lib/aarch64-linux-ohos。
                _seen = set()
                _probe = os.path.dirname(os.path.realpath(cxx))
                for _ in range(6):
                    if _probe in _seen:
                        break
                    _seen.add(_probe)
                    _found = False
                    for _sub in ("lib/aarch64-linux-ohos", "aarch64-linux-ohos/lib"):
                        _cand = os.path.join(_probe, _sub)
                        if os.path.isfile(os.path.join(_cand, "libc++_shared.so")):
                            run_env["LD_LIBRARY_PATH"] = (
                                _cand + os.pathsep + run_env.get("LD_LIBRARY_PATH", ""))
                            _found = True
                            break
                    if _found:
                        break
                    _probe = os.path.dirname(_probe)
                run_code, run_out, run_err = self._run_cmd(
                    run_cmd, timeout=300, cwd=run_dir, env=run_env)
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
        # Install headers: copy entire boost/ include directory
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

        # Install compiled static libraries (consumer-facing set: the 4
        # selected libraries; unit_test_framework is a test-only helper
        # archive and is not shipped in the package).
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_*.a")):
            base = os.path.basename(lib_file)
            if base == "libboost_unit_test_framework.a":
                continue
            copy(self, base, src=self.build_folder, dst=libdir)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")

        # Main "headers" component (always needed)
        self.cpp_info.components["boost_headers"].includedirs = ["include"]
        self.cpp_info.components["boost_headers"].set_property("cmake_target_name", "Boost::headers")

        # Filesystem
        self.cpp_info.components["boost_filesystem"].includedirs = []
        self.cpp_info.components["boost_filesystem"].libs = ["boost_filesystem"]
        self.cpp_info.components["boost_filesystem"].requires = ["boost_headers", "boost_system"]
        self.cpp_info.components["boost_filesystem"].set_property("cmake_target_name", "Boost::filesystem")

        # Regex
        self.cpp_info.components["boost_regex"].includedirs = []
        self.cpp_info.components["boost_regex"].libs = ["boost_regex"]
        self.cpp_info.components["boost_regex"].requires = ["boost_headers"]
        self.cpp_info.components["boost_regex"].set_property("cmake_target_name", "Boost::regex")

        # ProgramOptions
        self.cpp_info.components["boost_program_options"].includedirs = []
        self.cpp_info.components["boost_program_options"].libs = ["boost_program_options"]
        self.cpp_info.components["boost_program_options"].requires = ["boost_headers"]
        self.cpp_info.components["boost_program_options"].set_property("cmake_target_name", "Boost::program_options")

        # Iostreams
        self.cpp_info.components["boost_iostreams"].includedirs = []
        self.cpp_info.components["boost_iostreams"].libs = ["boost_iostreams"]
        self.cpp_info.components["boost_iostreams"].requires = ["boost_headers", "boost_system", "zlib::zlib"]
        self.cpp_info.components["boost_iostreams"].set_property("cmake_target_name", "Boost::iostreams")
        # System (header-only since 1.69, but CMake component still needed)
        self.cpp_info.components["boost_system"].includedirs = []
        self.cpp_info.components["boost_system"].libs = []
        self.cpp_info.components["boost_system"].requires = ["boost_headers"]
        self.cpp_info.components["boost_system"].set_property("cmake_target_name", "Boost::system")

        # DateTime (header-only since 1.69, but CMake component still needed)
        self.cpp_info.components["boost_date_time"].includedirs = []
        self.cpp_info.components["boost_date_time"].libs = []
        self.cpp_info.components["boost_date_time"].requires = ["boost_headers"]
        self.cpp_info.components["boost_date_time"].set_property("cmake_target_name", "Boost::date_time")
