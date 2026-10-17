#!/usr/bin/env python3
"""Conan recipe — boost1.84-random 1.84.0 (Boost.Random component package).

Boost b2 build system is incompatible with OHOS (E068), so we manually
compile the Boost.Random library source into a static archive, following
the approach proven in archives/b/boost/1.84.0.

Upstream source (libs/random/src): random_device.cpp — compiles cleanly on
OHOS (clang 15, libc++). The POSIX /dev/urandom backend is used (no
Windows CryptAPI), reading via open/read/close as on Linux.

Note on boost::system: random_device.cpp includes boost/system headers,
which are header-only since Boost 1.69, so no external dependency on a
compiled boost_system library is required.
"""
import os, glob, signal, subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostRandomConan(ConanFile):
    name = "boost1.84-random"
    version = "1.84.0"
    description = "Boost.Random 1.84.0 组件包（手动编译 libboost_random.a，鸿蒙 PC 适配）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    # Boost b2 build system is incompatible with OHOS, so we manually compile
    # the random library into a static archive (see notes.md for the rationale).

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
            # R8 compliance: skip pthread_setcancelstate (not available on OHOS musl)
            # via a feature-detection macro instead of a platform macro (__OHOS__).
            # The patch consumes BOOST_SP_NO_PTHREAD_SETCANCELSTATE, see patches/0001.
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
        ])

        # Random: random_device.cpp is the only compiled source upstream
        # (libs/random/src); the rest of Boost.Random is header-only.
        random_src = [
            "random_device.cpp",
        ]
        self._compile_lib("random", os.path.join(boost_root, "libs/random/src"), random_src, cxx, ar, cxxflags)

        # ⚠️ 上游测试集成（规则 5）：b2 构建系统在 OHOS 不兼容（SHELL 执行机制
        # 失败，E068 错误模式），无法直接运行 B2 测试目标。这里改为手动编译
        # random 库自带的测试源文件（绕过 b2）并真实运行，统计通过率写入报告
        # 文件供 CI 与 PR 描述回填。mt19937/mt19937_64 需要
        # boost_unit_test_framework（本配方未编译 test 库），按上游断言语义
        # 改用 boost/test/included/unit_test.hpp 单头全实现（同一套用例与
        # 断言，与上游 b2 run 的 BOOST_TEST_MAIN 行为等价）。
        self._run_upstream_tests(boost_root, cxx, cxxflags)

    def _run_cmd(self, cmd, timeout, shell=False, env=None):
        """Run a command with a hard timeout, killing the whole process group
        on timeout so no orphaned child (e.g. clang++) keeps the CI worker busy.

        stdin is redirected to DEVNULL: if an upstream test tries to read from
        stdin it immediately gets EOF instead of hanging (interactive-test
        protection, per CI environment-issue guidance).
        """
        proc = subprocess.Popen(
            cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, stdin=subprocess.DEVNULL, start_new_session=True,
            env=env)
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

    def _write_mt_test(self, dst_path, urng, extra_defines, body_ipp):
        """生成 mt 系列测试的 included 版包装（上游 test_generator.ipp 用
        linked 版 unit_test.hpp，需要 boost_unit_test_framework；此处改用
        boost/test/included/unit_test.hpp 单头全实现，宏定义与上游测试文件
        逐字一致，断言语义不变）。"""
        defines = "\n".join(f"#define {k} {v}" for k, v in extra_defines.items())
        content = f"""/* 上游 {os.path.basename(dst_path)} 的 included 版包装：
   原文件 include "test_generator.ipp"（其内部用 linked 版 unit_test.hpp），
   b2 上游通过链接 boost_unit_test_framework 提供实现；本配方未编译 test 库，
   改用 boost/test/included/unit_test.hpp 单头全实现，宏定义与上游测试文件
   逐字一致（断言与验证值不变）。 */
#define BOOST_TEST_MODULE {urng.split('::')[-1]}
#include <boost/test/included/unit_test.hpp>
#include <boost/random/mersenne_twister.hpp>
#include <algorithm>
#include <vector>
#include <boost/cstdint.hpp>
{defines}
#include "test_generator_body.ipp"
"""
        with open(dst_path, "w", encoding="utf-8") as fh:
            fh.write(content)

    def _run_upstream_tests(self, boost_root, cxx, cxxflags):
        """编译并运行 random 库的上游测试源文件（绕过 b2），统计通过率。

        测试文件来自 libs/random/test/ 与 libs/random/example/，编译后直接
        运行可执行文件，以退出码 0 判定通过。报告写入
        build_folder/upstream-tests-report.txt。
        """
        lib_dir = self.build_folder
        # OHOS 测试二进制运行时需要 SDK 的 libc++_shared.so（与 test_package
        # 的 _find_libcxx_dir 同源逻辑：clang++ -print-file-name 定位，无硬编码路径）
        try:
            libcxx_dir = os.path.dirname(subprocess.check_output(
                [cxx, "-print-file-name=libc++_shared.so"], text=True).strip())
        except Exception:  # noqa: BLE001 — 定位失败时退回裸 PATH 查找
            libcxx_dir = ""
        run_env = dict(os.environ)
        if libcxx_dir and os.path.isdir(libcxx_dir):
            run_env["LD_LIBRARY_PATH"] = (
                libcxx_dir + ":" + run_env.get("LD_LIBRARY_PATH", ""))

        # 从上游 test_generator.ipp 提取 body（保留全部断言逻辑，
        # 仅去掉 linked 版 unit_test.hpp 的 include 与 BOOST_TEST_MAIN 定义，
        # 由包装文件的 included/unit_test.hpp + BOOST_TEST_MODULE 承担）
        gen_ipp = os.path.join(boost_root, "libs/random/test/test_generator.ipp")
        with open(gen_ipp, "r", encoding="utf-8") as fh:
            body = fh.read()
        body = body.replace("#include <boost/test/unit_test.hpp>", "")
        body = body.replace("#define BOOST_TEST_MAIN", "")
        body_ipp = os.path.join(lib_dir, "test_generator_body.ipp")
        with open(body_ipp, "w", encoding="utf-8") as fh:
            fh.write(body)

        test_inc = os.path.join(boost_root, "libs/random/test")
        # (名称, 源文件或生成包装, 断言数)
        tests = []
        # 1) test_random_device.cpp：上游用 included/test_exec_monitor.hpp（无需 test 库），原样编译
        tests.append(("test_random_device",
                      os.path.join(boost_root, "libs/random/test/test_random_device.cpp"), 6))
        # 2) test_mt19937.cpp：linked 版 → included 版包装，宏逐字取自上游测试文件
        self._write_mt_test(
            os.path.join(lib_dir, "test_mt19937_inc.cpp"), "boost::random::mt19937",
            {
                "BOOST_RANDOM_URNG": "boost::random::mt19937",
                "BOOST_RANDOM_SEED_WORDS": "624",
                "BOOST_RANDOM_VALIDATION_VALUE": "4123659995U",
                "BOOST_RANDOM_SEED_SEQ_VALIDATION_VALUE": "666528879U",
                "BOOST_RANDOM_ITERATOR_VALIDATION_VALUE": "3408548740U",
                "BOOST_RANDOM_DISCARD_COUNT1": "9307",
                "BOOST_RANDOM_DISCARD_COUNT2": "20000000",
                "BOOST_RANDOM_GENERATE_VALUES": "{ 0xD091BB5CU, 0x22AE9EF6U, 0xE7E1FAEEU, 0xD5C31F79U }",
            }, body_ipp)
        tests.append(("test_mt19937",
                      os.path.join(lib_dir, "test_mt19937_inc.cpp"), 15))
        # 3) test_mt19937_64.cpp：同上，宏逐字取自上游测试文件
        self._write_mt_test(
            os.path.join(lib_dir, "test_mt19937_64_inc.cpp"), "boost::random::mt19937_64",
            {
                "BOOST_RANDOM_URNG": "boost::random::mt19937_64",
                "BOOST_RANDOM_SEED_WORDS": "624",
                "BOOST_RANDOM_VALIDATION_VALUE": "UINT64_C(9981545732273789042)",
                "BOOST_RANDOM_SEED_SEQ_VALIDATION_VALUE": "UINT64_C(12176471137395770412)",
                "BOOST_RANDOM_ITERATOR_VALIDATION_VALUE": "UINT64_C(13543700832025962283)",
                "BOOST_RANDOM_GENERATE_VALUES": "{ 0xF6F6AEA6U, 0xC96D191CU, 0x8BC80F1CU, 0x401F7AC7U }",
            }, body_ipp)
        tests.append(("test_mt19937_64",
                      os.path.join(lib_dir, "test_mt19937_64_inc.cpp"), 15))
        # 4) random_demo.cpp：上游 example（Jamfile 中 run 目标），纯 header-only
        tests.append(("random_demo",
                      os.path.join(boost_root, "libs/random/example/random_demo.cpp"), 0))

        report_lines = []
        passed, failed = 0, 0
        for name, src, asserts in tests:
            exe = os.path.join(lib_dir, f"run_{name}")
            cmd_compile = (
                f"{cxx} {cxxflags} -I{lib_dir} -I{test_inc} {src} "
                f"-L{lib_dir} -lboost_random -o {exe}")
            ret_code, ret_out, ret_err = self._run_cmd(cmd_compile, timeout=300, shell=True)
            if ret_code != 0:
                report_lines.append(f"COMPILE_FAIL {name}: {ret_err.splitlines()[-1] if ret_err else ''}")
                failed += 1
                continue
            run_code, run_out, run_err = self._run_cmd([exe], timeout=420, env=run_env)
            ok = run_code == 0
            report_lines.append(f"{'PASS' if ok else 'FAIL'} {name} (断言≈{asserts}) rc={run_code}")
            if ok:
                passed += 1
            else:
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

        # Random
        self.cpp_info.components["boost_random"].includedirs = []
        self.cpp_info.components["boost_random"].libs = ["boost_random"]
        self.cpp_info.components["boost_random"].requires = ["boost_headers"]
        self.cpp_info.components["boost_random"].set_property("cmake_target_name", "Boost::random")

        # System (header-only since 1.69, but CMake component still needed for
        # random_device's boost::system::error_code usage)
        self.cpp_info.components["boost_system"].includedirs = []
        self.cpp_info.components["boost_system"].libs = []
        self.cpp_info.components["boost_system"].requires = ["boost_headers"]
        self.cpp_info.components["boost_system"].set_property("cmake_target_name", "Boost::system")
