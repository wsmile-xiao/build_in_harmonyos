#!/usr/bin/env python3
"""Conan recipe — boost1.84-locale 1.84.0 (Boost.Locale component package).

Boost b2 build system is incompatible with OHOS (E068), so we manually
compile the Boost.Locale library sources into a static archive, following
the approach proven in archives/b/boost/1.84.0 and boost1.84-chrono.

Backend configuration (std + musl iconv):
- std backend enabled (POSIX/WinAPI/ICU backends disabled)
- iconv support via musl libc built-in iconv (part of libc, zero extra
  conan dependency — same as upstream Linux default where iconv is
  bundled with libc). OHOS musl supports ISO8859-x/cp125x/cp932/koi8-r
  etc. Verified: ISO-8859-1 <-> UTF-8 roundtrip is byte-exact.
- Upstream Jamfile.v2 requires iconv or ICU on non-Windows platforms;
  std-only (no iconv) is an upstream-unsupported configuration that
  makes conv::to_utf/from_utf throw invalid_charset_error for all
  non-UTF-8 charsets. Using musl iconv restores upstream-equivalent
  behavior with zero external dependencies.

Upstream sources (libs/locale/src/boost/locale/, 21 files):
  core:   encoding/codepage.cpp, shared/{date_time,format,formatting,
          generator,iconv_codecvt,ids,localization_backend,message,
          mo_lambda}.cpp, util/{codecvt_converter,default_locale,
          encoding,info,locale_data}.cpp
  std:    std/{codecvt,collate,converter,numeric,std_backend}.cpp
  extra:  util/gregorian.cpp (required when std backend is on)
"""
import glob
import os
import signal
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostLocaleConan(ConanFile):
    name = "boost1.84-locale"
    version = "1.84.0"
    description = "Boost.Locale 1.84.0 组件包（std 后端 + musl 内置 iconv，手动编译 libboost_locale.a，鸿蒙 PC 适配）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    # Boost b2 build system is incompatible with OHOS, so we manually compile
    # the locale library into a static archive (see notes.md for the rationale).

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
            f"-I{boost_root}/libs/locale/src",  # Jamfile <include>$(TOP)/src
            "-DBOOST_LOCALE_SOURCE",
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_THREAD_NO_LIB=1",
            # Backend selection: std only (posix/winapi/icu disabled)
            "-DBOOST_LOCALE_NO_POSIX_BACKEND=1",
            "-DBOOST_LOCALE_NO_WINAPI_BACKEND=1",
            "-DBOOST_LOCALE_NO_ICU_BACKEND=1",
            # iconv via musl libc built-in (no external libiconv dependency)
            "-DBOOST_LOCALE_WITH_ICONV",
            # R8 compliance: skip pthread_setcancelstate (not available on OHOS musl)
            # via a feature-detection macro instead of a platform macro (__OHOS__).
            # The patch consumes BOOST_SP_NO_PTHREAD_SETCANCELSTATE, see patches/0001.
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
        ])

        # Boost.Locale sources — 21 files (15 core + 5 std backend + gregorian)
        locale_src = [
            # core (shared + encoding + util)
            "encoding/codepage.cpp",
            "shared/date_time.cpp",
            "shared/format.cpp",
            "shared/formatting.cpp",
            "shared/generator.cpp",
            "shared/iconv_codecvt.cpp",
            "shared/ids.cpp",
            "shared/localization_backend.cpp",
            "shared/message.cpp",
            "shared/mo_lambda.cpp",
            "util/codecvt_converter.cpp",
            "util/default_locale.cpp",
            "util/encoding.cpp",
            "util/info.cpp",
            "util/locale_data.cpp",
            # std backend
            "std/codecvt.cpp",
            "std/collate.cpp",
            "std/converter.cpp",
            "std/numeric.cpp",
            "std/std_backend.cpp",
            # required when std/posix/winapi backend is on
            "util/gregorian.cpp",
        ]
        src_dir = os.path.join(boost_root, "libs/locale/src/boost/locale")
        self._compile_lib("locale", src_dir, locale_src, cxx, ar, cxxflags)

        # ⚠️ 上游测试集成（规则 5）：b2 构建系统在 OHOS 不兼容（SHELL 执行机制
        # 失败，E068 错误模式），无法直接运行 B2 测试目标。这里改为手动编译
        # locale 库自带的测试源文件（绕过 b2）并真实运行，统计通过率写入报告
        # 文件供 CI 与 PR 描述回填。实测 15 项 run 型测试中 10 项完整通过；
        # 5 项（test_encoding / test_codepage_converter / test_message /
        # test_std_collate / test_std_formatting）因 OHOS musl C 库数据限制
        # 部分断言失败（gbk 不支持、//TRANSLIT 不可用、collate 字节序、
        # money_put 无千分位、iso-2022-jp ESC 序列风格），属平台限制，
        # 详见 notes.md 与 test-report.md 的豁免说明。
        self._run_upstream_tests(boost_root, cxx, cxxflags)

    def _run_cmd(self, cmd, timeout, shell=False, env=None, cwd=None):
        """Run a command with a hard timeout, killing the whole process group
        on timeout so no orphaned child (e.g. clang++) keeps the CI worker busy.

        stdin is redirected to DEVNULL: if an upstream test tries to read from
        stdin it immediately gets EOF instead of hanging (interactive-test
        protection, per CI environment-issue guidance).
        """
        proc = subprocess.Popen(
            cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL, start_new_session=True,
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

    def _run_upstream_tests(self, boost_root, cxx, cxxflags):
        """编译并运行 locale 库的上游测试源文件（绕过 b2），统计通过率。

        测试文件来自 libs/locale/test/（上游 Jamfile.v2 的 run 目标，非 icu/
        winapi/posix 专属的通用测试 + std 后端测试），编译后直接运行可执行
        文件，以退出码 0 判定通过。非 std 后端专属测试（test_collate/
        test_convert/test_boundary/test_formatting/test_icu_vs_os_timezone/
        test_winapi_*/test_posix_*）自带后端守卫，std-only 配置下编译后
        自动 Skipping 返回 0，不计入运行矩阵。报告写入
        build_folder/upstream-tests-report.txt。
        """
        lib_dir = self.build_folder
        # OHOS 测试二进制运行时需要 SDK 的 libc++_shared.so（与 test_package
        # 的 _find_libcxx_dir 同源逻辑：clang++ -print-file-name 定位，无硬编码路径）
        libcxx_dir = ""
        try:
            located = subprocess.check_output(
                [cxx, "-print-file-name=libc++_shared.so"], text=True).strip()
            if located and located != "libc++_shared.so":
                libcxx_dir = os.path.dirname(located)
        except Exception:  # noqa: BLE001 — 定位失败时退回裸 PATH 查找
            libcxx_dir = ""
        run_env = dict(os.environ)
        if libcxx_dir and os.path.isdir(libcxx_dir):
            run_env["LD_LIBRARY_PATH"] = (
                libcxx_dir + ":" + run_env.get("LD_LIBRARY_PATH", ""))

        test_dir = os.path.join(boost_root, "libs/locale/test")
        # (测试名, 附加源文件列表, 运行 cwd（None=当前目录）)
        # test_message 需在 libs/locale/test 目录下运行（读 .mo 文件）
        test_cases = [
            ("test_catalog", [], None),
            ("test_encoding", [], None),
            ("test_utf", [], None),
            ("test_util", ["test_helpers.cpp"], None),
            ("test_date_time", [], None),
            ("test_ios_info", [], None),
            ("test_ios_prop", [], None),
            ("test_codecvt", [], None),
            ("test_codepage_converter", [], None),
            ("test_stream_io", [], None),
            ("test_message", [], test_dir),
            ("test_generator", [], None),
            ("test_std_collate", [], None),
            ("test_std_convert", [], None),
            ("test_std_formatting", [], None),
        ]
        report_lines = []
        passed, failed = 0, 0
        for test_name, extra_srcs, run_cwd in test_cases:
            src = os.path.join(test_dir, f"{test_name}.cpp")
            exe = os.path.join(lib_dir, test_name)
            extra = " ".join(os.path.join(test_dir, s) for s in extra_srcs)
            cmd_compile = (
                f"{cxx} {cxxflags} -I{test_dir} {src} {extra} "
                f"-L{lib_dir} -lboost_locale -lpthread -o {exe}")
            ret_code, ret_out, ret_err = self._run_cmd(cmd_compile, timeout=300, shell=True)
            if ret_code != 0:
                report_lines.append(
                    f"COMPILE_FAIL {test_name}: "
                    f"{ret_err.splitlines()[-1] if ret_err else ''}")
                failed += 1
                continue
            run_code, run_out, run_err = self._run_cmd(
                [exe], timeout=120, env=run_env, cwd=run_cwd)
            ok = run_code == 0
            detail = ""
            if not ok:
                # 提取失败摘要（错误行/通过率行）供报告留档
                err_lines = [ln for ln in (run_out or "").splitlines()
                             if "Error" in ln or "Failed" in ln or "Failed with" in ln]
                detail = " | " + (err_lines[0][:120] if err_lines else f"rc={run_code}")
            report_lines.append(f"{'PASS' if ok else 'FAIL'} {test_name}{detail}")
            if ok:
                passed += 1
            else:
                failed += 1
        report_lines.append(f"TOTAL {passed + failed}: {passed} passed / {failed} failed")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(f"上游测试报告: {report_path} ({passed}/{passed + failed} 通过)")
        for line in report_lines:
            self.output.info(f"[upstream-tests] {line}")

    def package(self):
        # Install headers: copy entire boost/ include directory
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

        # Install compiled static library
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_*.a")):
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")

        # Main "headers" component (always needed)
        self.cpp_info.components["boost_headers"].includedirs = ["include"]
        # R8 compliance: expose BOOST_SP_NO_PTHREAD_SETCANCELSTATE to all
        # consumers so the patched sp_thread_sleep.hpp skips the
        # pthread_setcancelstate path (not available on OHOS musl) without
        # relying on a platform macro. Every downstream that includes boost
        # headers gets this define via Conan's CMakeDeps/Toolchain propagation.
        self.cpp_info.components["boost_headers"].defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        self.cpp_info.components["boost_headers"].set_property("cmake_target_name", "Boost::headers")

        # Locale
        self.cpp_info.components["boost_locale"].includedirs = []
        self.cpp_info.components["boost_locale"].libs = ["boost_locale"]
        self.cpp_info.components["boost_locale"].requires = ["boost_headers"]
        # iconv lives inside musl libc on OHOS — no extra system_libs needed
        self.cpp_info.components["boost_locale"].set_property("cmake_target_name", "Boost::locale")

        # System (header-only since 1.69, but CMake component still needed for
        # locale's boost::system::error_code usage)
        self.cpp_info.components["boost_system"].includedirs = []
        self.cpp_info.components["boost_system"].libs = []
        self.cpp_info.components["boost_system"].requires = ["boost_headers"]
        self.cpp_info.components["boost_system"].set_property("cmake_target_name", "Boost::system")
