#!/usr/bin/env python3
"""Conan recipe — boost1.84-iostreams 1.84.0 (Boost.Iostreams split package).

Boost 1.84.0 组件拆分包之一：仅交付 Boost.Iostreams（libboost_iostreams.a）。
底稿：archives/b/boost/1.84.0 元包（其 iostreams 段编译参考）与
boost1.84-atomic/wave/log 组件包（手动裁剪编译模式）。

形态选型（见 notes.md）：独立裁剪包（非 requires 元包）。原因：
- 元包虽编译了 libboost_iostreams.a 且声明了 boost_iostreams 组件，但其
  iostreams 只编了 4 个 TU（file_descriptor/mapped_file/zlib/gzip）且未带
  上游 Jamfile 要求的 BOOST_IOSTREAMS_USE_DEPRECATED 宏（deprecated
  构造/open 重载符号缺失，deprecated_file_descriptor_test 链接失败）；
- 元包 iostreams 无 bzip2 支持（上游 Jamfile 在系统有 libbz2 时编入
  bzip2.cpp）；本组件包补齐 zlib + bzip2 双压缩后端（bzip2/1.0.8 制品仓
  在库，W0 已验证）；
- 独立包版本演进不与元包修订锁死（R37），cmake_file_name 用包名避免与
  元包 "Boost" 的 CMakeDeps 冲突（同 atomic/log/wave 先例）。

**源码清单（libs/iostreams/build/Jamfile.v2 权威）**：
  lib boost_iostreams : file_descriptor.cpp mapped_file.cpp
    + zlib-requirements (zlib.cpp gzip.cpp，NO_ZLIB 未设)
    + bzip2-requirements (bzip2.cpp，NO_BZIP2 未设)
    + <define>BOOST_IOSTREAMS_USE_DEPRECATED
  lzma.cpp/zstd.cpp 需要 liblzma/libzstd（本包不引入，同元包口径），
  bzip2/lzma 可选项中仅启用 zlib+bzip2。

**上游测试（libs/iostreams/test/Jamfile.v2 test-suite iostreams）**：
  上游测试注册条目 56（grep 口径：test-iostreams 53 行含 1 个 rule
  定义行、compile-fail-iostreams 2 行含 1 个 rule 定义行、test-suite
  汇总 1 行），真实测试目标 53 = 无条件 45（44 run + 1 compile-fail）
  + 条件 8（bzip2_test、zlib 块 write_failure/gzip/zlib_test、
  lzma_test、zstd_test 由 NO_BZIP2/NO_ZLIB/NO_LZMA/NO_ZSTD 变量门控；
  large_file_test×2 由 LARGE_FILE_KEEP/LARGE_FILE_TEMP 环境变量门控）。
  本配置（非 Windows + zlib/bzip2 后端启用 + lzma/zstd 未引入 +
  LARGE_FILE_* 未设）生效 48 项：43 单源/双源 run（含 code_converter
  双源、deprecated_file_descriptor 带 USE_DEPRECATED 宏的 run 型）+
  bzip2/gzip/zlib/write_failure 4 个已启用后端条件测试 + compile-fail
  型 1 项，在 build() 中手动编译并真实运行（b2 在 OHOS 不兼容 E068，
  绕过 b2）。未执行的 5 项均为上游条件/平台门控（windows_pipe 非
  Windows 不构建、lzma/zstd 后端未启用、large_file×2 环境变量未设），
  非适配删减。
  测试框架 boost_unit_test_framework（19 TU）、测试夹具 boost_filesystem
  （9 TU）/boost_regex（5 TU，grep_test/regex_filter_test 需要）为测试期
  依赖，仅编译不入 package 产物（同 log/serialization 组件包先例）。
"""
import glob
import os
import signal
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostIostreamsConan(ConanFile):
    name = "boost1.84-iostreams"
    version = "1.84.0"
    description = "Boost.Iostreams 1.84.0 拆分组件包（libboost_iostreams 静态库，zlib+bzip2 压缩后端，鸿蒙 PC 适配）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = "https://github.com/boostorg/iostreams"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    # Boost 源码树 5 万+文件，在 OHOS HMDFS 上整体复制到 build folder 极慢
    # （实测 >13 分钟未完成）。本配方对源码只读（补丁经 conan patch 机制
    # 应用后不改源内其他文件），直接在 source_folder 上编译，跳过复制
    # （conan no_copy_source 标准语义，同 atomic/log/wave 组件包）。
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 压缩后端：zlib（zlib.cpp/gzip.cpp）+ bzip2（bzip2.cpp）。
        # 上游 Jamfile 在系统库存在时启用对应压缩源（NO_ZLIB/NO_BZIP2
        # 未设），本包全启用两者。
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8")

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def _cxx(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        return compilers.get("cpp", "clang++")

    def _ar(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        return compilers.get("ar", "llvm-ar")

    def _cxxflags(self, boost_root):
        # Optimization flags driven by build_type (R8: no hardcoded build profile).
        if self.settings.build_type == "Debug":
            opt_flags = ["-O0", "-g"]
        else:
            opt_flags = ["-O2", "-DNDEBUG"]
        # 依赖头文件（zlib.h/bzlib.h）来自 conan 依赖包的 package_folder。
        zlib_inc = os.path.join(
            self.dependencies["zlib"].package_folder, "include")
        bzip2_inc = os.path.join(
            self.dependencies["bzip2"].package_folder, "include")
        return " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            *opt_flags,
            "-fPIC",
            f"-I{boost_root}",
            f"-I{zlib_inc}",
            f"-I{bzip2_inc}",
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_SYSTEM_NO_DEPRECATED",
            "-DBOOST_IOSTREAMS_NO_LIB",
            # R8: patched sp_thread_sleep.hpp skips pthread_setcancelstate
            # (not available on OHOS musl) — see patches/0001.
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
            # 上游 Jamfile line 120：<define>BOOST_IOSTREAMS_USE_DEPRECATED
            # （deprecated 构造/open 重载的实现守卫，缺失则
            # deprecated_file_descriptor_test 链接失败）
            "-DBOOST_IOSTREAMS_USE_DEPRECATED",
        ])

    def _compile_lib(self, lib_name, src_files, cxxflags, obj_dirname=None):
        """Compile source files and archive into a static library.

        obj 命名用「相对 boost_root 路径转下划线」保持唯一（见
        boost1.84-url 的 ar 同名覆盖教训）。
        """
        cxx, ar = self._cxx(), self._ar()
        objects = []
        obj_dir = os.path.join(self.build_folder, obj_dirname or f"obj_{lib_name}")
        os.makedirs(obj_dir, exist_ok=True)
        for src in src_files:
            rel = os.path.relpath(src, self.source_folder)
            obj_name = rel.replace("/", "_").replace(".cpp", ".o")
            obj_path = os.path.join(obj_dir, obj_name)
            self.run(f'"{cxx}" {cxxflags} -c "{src}" -o "{obj_path}"')
            objects.append(obj_path)
        lib_path = os.path.join(self.build_folder, f"libboost_{lib_name}.a")
        self.run(f'"{ar}" rcs "{lib_path}" {" ".join(objects)}')
        return lib_path

    def build(self):
        apply_conandata_patches(self)
        boost_root = self.source_folder
        cxxflags = self._cxxflags(boost_root)

        # ── Iostreams component (5 TU, libs/iostreams/build/Jamfile.v2) ──
        # sources = file_descriptor.cpp mapped_file.cpp
        #         + zlib.cpp gzip.cpp (zlib enabled) + bzip2.cpp (bzip2 enabled)
        # lzma.cpp/zstd.cpp excluded（上游在系统库存在时才编入；本包未引入
        # liblzma/libzstd 依赖，同元包口径）。
        io_src = [
            os.path.join(boost_root, "libs", "iostreams", "src", f)
            for f in ["file_descriptor.cpp", "mapped_file.cpp",
                      "zlib.cpp", "gzip.cpp", "bzip2.cpp"]
        ]
        self._compile_lib("iostreams", io_src, cxxflags)

        # ── Upstream tests (rule 5): compile & run the real test-suite ──
        self._run_upstream_tests(boost_root, cxxflags)

    def _run_cmd(self, cmd, timeout, shell=False, env=None):
        """Run a command with a hard timeout, killing the whole process group
        on timeout so no orphaned child (e.g. clang++) keeps the CI worker busy.

        stdin is redirected to DEVNULL: if an upstream test tries to read from
        stdin it immediately gets EOF instead of hanging (interactive-test
        protection, per CI environment-issue guidance).
        """
        proc = subprocess.Popen(
            cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, stdin=subprocess.DEVNULL, start_new_session=True, env=env)
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
        cxx = self._cxx()
        try:
            out = subprocess.check_output(
                [cxx, "-print-file-name=libc++_shared.so"], text=True).strip()
        except Exception as exc:  # noqa: BLE001 — introspection failure is reported below
            self.output.warning(f"libc++_shared.so introspection failed: {exc}")
            return None
        if not out or out == "libc++_shared.so":
            return None
        return os.path.dirname(out)

    def _run_upstream_tests(self, boost_root, cxxflags):
        """编译并运行 Boost.Iostreams 上游测试（绕过 b2），统计通过率。

        上游 libs/iostreams/test/Jamfile.v2 test-suite iostreams 测试注册
        条目 56（三模式 grep 口径，含 2 个 rule 定义行 + 1 个汇总行），
        真实测试目标 53 个（无条件 45 = 44 run + 1 compile-fail；条件 8 =
        bzip2/zlib 块 4 + lzma/zstd 2 + large_file×2）。本配置生效的
        48 项（非 Windows、zlib/bzip2 后端启用、lzma/zstd 未引入、
        LARGE_FILE_* 环境变量未设）：
          - run 型 47 项（含 deprecated_file_descriptor_test 的
            BOOST_IOSTREAMS_USE_DEPRECATED 宏变体、code_converter_test
            的 detail/utf8_codecvt_facet.cpp 附加源、grep/regex_filter
            的 boost_regex 依赖、已启用后端的 zlib/gzip/bzip2/
            write_failure 压缩 4 项）
          - compile-fail 型 1 项（deprecated_file_descriptor_test 不带宏
            编译应失败）
        未执行的 5 项均为上游条件/平台门控（windows_pipe_test 非
        Windows 平台上游自身不构建、lzma_test/zstd_test 对应后端本包
        未启用、large_file_test×2 需 LARGE_FILE_KEEP/LARGE_FILE_TEMP
        环境变量），非适配删减。
        测试框架依赖（仅编译不入 package 产物）：
          - boost_unit_test_framework：19 TU（libs/test/build/Jamfile.v2
            UTF_SOURCES，同 log 组件包先例）
          - boost_filesystem：9 TU（test 夹具 temp_file/operations 用）
          - boost_regex：5 TU（grep_test/regex_filter_test 用，元包同款清单）
        """
        cxx, ar = self._cxx(), self._ar()
        lib_dir = self.build_folder
        test_dir = os.path.join(boost_root, "libs", "iostreams", "test")
        zlib_lib = os.path.join(
            self.dependencies["zlib"].package_folder, "lib")
        bzip2_lib = os.path.join(
            self.dependencies["bzip2"].package_folder, "lib")

        # 1) 测试辅助库：boost_unit_test_framework（19 TU）
        utf_src = [
            os.path.join(boost_root, "libs", "test", "src", f)
            for f in [
                "compiler_log_formatter.cpp", "debug.cpp", "decorator.cpp",
                "execution_monitor.cpp", "framework.cpp",
                "plain_report_formatter.cpp", "progress_monitor.cpp",
                "results_collector.cpp", "results_reporter.cpp",
                "test_framework_init_observer.cpp", "test_tools.cpp",
                "test_tree.cpp", "unit_test_log.cpp", "unit_test_main.cpp",
                "unit_test_monitor.cpp", "unit_test_parameters.cpp",
                "junit_log_formatter.cpp", "xml_log_formatter.cpp",
                "xml_report_formatter.cpp",
            ]
        ]
        utf_flags = cxxflags + " -DBOOST_TEST_NO_LIB"
        self._compile_lib("unit_test_framework", utf_src, utf_flags,
                          obj_dirname="obj_utf_testonly")

        # 2) 测试辅助库：boost_filesystem（9 TU，tmpnam/unique_path 夹具）
        fs_src = [
            os.path.join(boost_root, "libs", "filesystem", "src", f)
            for f in [
                "codecvt_error_category.cpp", "directory.cpp", "exception.cpp",
                "operations.cpp", "path.cpp", "path_traits.cpp",
                "portability.cpp", "unique_path.cpp", "utf8_codecvt_facet.cpp",
            ]
        ]
        fs_flags = (cxxflags + " -DBOOST_FILESYSTEM_NO_CXX20_CHAR8_T"
                    " -DBOOST_FILESYSTEM_NO_CXX20_ATOMIC_REF")
        self._compile_lib("filesystem", fs_src, fs_flags,
                          obj_dirname="obj_fs_testonly")

        # 3) 测试辅助库：boost_regex（5 TU，grep_test/regex_filter_test）
        re_src = [
            os.path.join(boost_root, "libs", "regex", "src", f)
            for f in ["posix_api.cpp", "regex.cpp", "regex_debug.cpp",
                      "static_mutex.cpp", "wide_posix_api.cpp"]
        ]
        self._compile_lib("regex", re_src, cxxflags,
                          obj_dirname="obj_re_testonly")

        # OHOS: 上游测试二进制动态依赖 SDK 的 libc++_shared.so，测试运行时
        # 通过编译器自省定位并注入 LD_LIBRARY_PATH（无硬编码 SDK 版本路径）。
        libcxx_dir = self._find_libcxx_dir() if self.settings.os == "OHOS" else None
        run_env = os.environ.copy()
        if libcxx_dir:
            run_env["LD_LIBRARY_PATH"] = (
                f"{libcxx_dir}:{run_env.get('LD_LIBRARY_PATH', '')}"
            )

        # 4) run 型 46 项（(测试名, 附加源/宏) 清单对齐上游 Jamfile）
        test_flags = cxxflags + f" -I{test_dir}"
        link_flags = (f'-L"{lib_dir}" -lboost_iostreams -lboost_filesystem '
                      f'-lboost_regex -lboost_unit_test_framework '
                      f'-L"{zlib_lib}" -lz -L"{bzip2_lib}" -lbz2')
        run_tests = [
            ("array_test.cpp", ""),
            ("auto_close_test.cpp", ""),
            ("buffer_size_test.cpp", ""),
            ("close_test.cpp", ""),
            ("code_converter_test.cpp", "EXTRA:detail/utf8_codecvt_facet.cpp"),
            ("combine_test.cpp", ""),
            ("compose_test.cpp", ""),
            ("component_access_test.cpp", ""),
            ("copy_test.cpp", ""),
            ("counter_test.cpp", ""),
            ("deprecated_file_descriptor_test.cpp", "MACRO:BOOST_IOSTREAMS_USE_DEPRECATED"),
            ("direct_adapter_test.cpp", ""),
            ("dual_seekable_test.cpp", ""),
            ("example_test.cpp", ""),
            ("execute_test.cpp", ""),
            ("file_test.cpp", ""),
            ("file_descriptor_test.cpp", ""),
            ("filtering_stream_test.cpp", ""),
            ("finite_state_filter_test.cpp", ""),
            ("flush_test.cpp", ""),
            ("grep_test.cpp", ""),
            ("invert_test.cpp", ""),
            ("line_filter_test.cpp", ""),
            ("mapped_file_test.cpp", ""),
            ("newline_test.cpp", ""),
            ("null_test.cpp", ""),
            ("operation_sequence_test.cpp", ""),
            ("path_test.cpp", ""),
            ("pipeline_test.cpp", ""),
            ("read_nonblocking_test.cpp", ""),
            ("regex_filter_test.cpp", ""),
            ("restrict_test.cpp", ""),
            ("seekable_file_test.cpp", ""),
            ("seekable_filter_test.cpp", ""),
            ("sequence_test.cpp", ""),
            ("slice_test.cpp", ""),
            ("stdio_filter_test.cpp", ""),
            ("stream_offset_32bit_test.cpp", ""),
            ("stream_offset_64bit_test.cpp", ""),
            ("stream_state_test.cpp", ""),
            ("symmetric_filter_test.cpp", ""),
            ("tee_test.cpp", ""),
            ("wide_stream_test.cpp", ""),
            ("write_failure_test.cpp", ""),
            ("bzip2_test.cpp", ""),
            ("gzip_test.cpp", ""),
            ("zlib_test.cpp", ""),
        ]
        # compile-fail 型 1 项：deprecated_file_descriptor_test.cpp 不带
        # USE_DEPRECATED 宏编译应失败（上游 compile-fail-iostreams 规则）
        compile_fail_tests = [
            ("deprecated_file_descriptor_test.cpp",
             "deprecated_file_descriptor_fail"),
        ]

        report_lines = []
        passed, failed = 0, 0

        def record(ok, line):
            nonlocal passed, failed
            report_lines.append(f"{'PASS' if ok else 'FAIL'} {line}")
            if ok:
                passed += 1
            else:
                failed += 1

        for src_name, extra in run_tests:
            src = os.path.join(test_dir, src_name)
            exe = os.path.join(lib_dir, "test_" + src_name.replace(".cpp", ""))
            extra_flags = ""
            extra_srcs = ""
            if extra.startswith("MACRO:"):
                extra_flags = f" -D{extra[6:]}"
            elif extra.startswith("EXTRA:"):
                extra_srcs = f' "{os.path.join(test_dir, extra[6:])}"'
            cmd = (f'"{cxx}" {test_flags}{extra_flags} "{src}"{extra_srcs} '
                   f'{link_flags} -o "{exe}"')
            ret_code, _, ret_err = self._run_cmd(cmd, timeout=300, shell=True)
            if ret_code != 0:
                record(False, f"{src_name} COMPILE_FAIL: "
                              f"{ret_err.splitlines()[-1] if ret_err.strip() else ''}")
                continue
            run_code, run_out, run_err = self._run_cmd([exe], timeout=300, env=run_env)
            ok = run_code == 0
            detail = (run_out or run_err or "").strip().splitlines()
            record(ok, f"{src_name} rc={run_code}"
                       f"{f' ({detail[-1]})' if detail else ''}")

        for src_name, target_name in compile_fail_tests:
            src = os.path.join(test_dir, src_name)
            # compile-fail 检查必须去掉库编译用的 USE_DEPRECATED 宏
            # （上游 compile-fail-iostreams 规则不带宏编译，deprecated
            # 重载声明消失 → 编译应失败）。
            fail_flags = test_flags.replace(
                " -DBOOST_IOSTREAMS_USE_DEPRECATED", "")
            cmd = f'"{cxx}" {fail_flags} -fsyntax-only "{src}"'
            ret_code, _, _ = self._run_cmd(cmd, timeout=120, shell=True)
            record(ret_code != 0,
                   f"{src_name} (compile-fail expectation {target_name}, rc={ret_code})")

        report_lines.append(f"TOTAL {passed + failed}: {passed} passed / {failed} failed")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(f"上游测试报告: {report_path} ({passed}/{passed + failed} 通过)")
        for line in report_lines[-5:]:
            self.output.info(f"[upstream-tests] {line}")
        if failed:
            raise Exception(f"Upstream tests failed: {failed}/{passed + failed} "
                            f"— see {report_path}")

    def package(self):
        # Full Boost header tree (patched): component package is self-contained
        # (Debian libboost-iostreams1.84-dev 同模式), downstream consumers do
        # not need the boost/1.84.0 meta package installed first.
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

        # Install the compiled static library (only libboost_iostreams.a —
        # the UTF/filesystem/regex archives are test-only, not packaged).
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_iostreams.a")):
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

    def package_info(self):
        # 拆分组件包使用独立的 CMake 包名 boost1.84-iostreams，避免与
        # boost/1.84.0 元包的 cmake_file_name "Boost" 冲突（同一工程
        # 同时依赖两者时 CMakeDeps 生成文件不会互相覆盖，同 atomic/
        # log/wave 组件包先例）。
        self.cpp_info.set_property("cmake_file_name", "boost1.84-iostreams")

        # Main "headers" component (always needed)
        self.cpp_info.components["boost1.84_iostreams_headers"].includedirs = ["include"]
        # R8 合规：向所有消费者暴露 BOOST_SP_NO_PTHREAD_SETCANCELSTATE，
        # 使打过补丁的 sp_thread_sleep.hpp 跳过 pthread_setcancelstate
        # 路径（OHOS musl 无此 API）。iostreams TU 与下游用户经 smart_ptr
        # 头链触及该文件。
        self.cpp_info.components["boost1.84_iostreams_headers"].defines = [
            "BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        self.cpp_info.components["boost1.84_iostreams_headers"].set_property(
            "cmake_target_name", "boost1.84-iostreams::headers")

        # iostreams (the component this package delivers)
        self.cpp_info.components["boost1.84_iostreams"].includedirs = []
        self.cpp_info.components["boost1.84_iostreams"].libs = ["boost_iostreams"]
        # 上游 Jamfile 传递压缩后端链接：zlib.cpp/gzip.cpp 用 zlib，
        # bzip2.cpp 用 bzip2（系统压缩库，Debian libboost-iostreams 同款
        # 传递依赖）。
        self.cpp_info.components["boost1.84_iostreams"].requires = [
            "boost1.84_iostreams_headers", "zlib::zlib", "bzip2::bzip2"]
        self.cpp_info.components["boost1.84_iostreams"].set_property(
            "cmake_target_name", "boost1.84-iostreams::iostreams")
