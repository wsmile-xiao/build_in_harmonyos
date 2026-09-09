#!/usr/bin/env python3
"""Conan recipe — boost1.84-atomic 1.84.0 (Boost.Atomic split package).

Boost 1.84.0 组件拆分包之一：仅交付 Boost.Atomic（libboost_atomic.a）。
底稿：archives/b/boost/1.84.0/ 元包（filesystem/regex/program_options/iostreams）。

形态选型（见 notes.md）：独立裁剪包（非 requires 元包）。原因：
- boost/1.84.0 元包只编译了 filesystem/regex/program_options/iostreams
  四个库，其 package_info 未声明 boost_atomic 组件、lib/ 无
  libboost_atomic.a——requires 元包拿不到 `Boost::atomic` 目标；
- Boost.Atomic 的 wait/notify API 并非 header-only：上游
  libs/atomic/build/Jamfile.v2 定义 `lib boost_atomic : lock_pool.cpp`
  （aarch64 Linux/OHOS 上仅此一个翻译单元；find_address_sse2/sse41
  仅 x86，wait_on_address.cpp 仅 Windows）；
- 独立包版本演进不与元包修订锁死，CI L5 产物基线干净（有 lib/ 产出）。

Boost b2 build system is incompatible with OHOS (E068, see meta-package
notes.md), so we manually compile the atomic sources into a static archive,
mirroring the meta-package recipe approach. lock_pool selects the futex
path on OHOS (musl libc supports the futex syscall) — verified working.
"""
import glob
import os
import signal
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostAtomicConan(ConanFile):
    name = "boost1.84-atomic"
    version = "1.84.0"
    description = "Boost.Atomic 1.84.0 拆分组件包（libboost_atomic 静态库，鸿蒙 PC 适配）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    # Boost b2 build system is incompatible with OHOS, so we manually compile
    # the atomic source into a static archive (same rationale as the
    # boost/1.84.0 meta package recipe).
    # Boost 源码树 5 万+文件，在 OHOS HMDFS 上整体复制到 build folder 极慢
    # （实测 >13 分钟未完成）。本配方对源码只读（无补丁、无源内生成物），
    # 直接在 source_folder 上编译，跳过复制（conan no_copy_source 标准语义）。
    no_copy_source = True

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
        # Jamfile.v2 requirements replicated: <include>../src (lock_pool.cpp
        # iterates lock_pool_init1.ipp via Boost.Preprocessor from there) and
        # <define>BOOST_ATOMIC_SOURCE.
        cxxflags = " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            *opt_flags,
            "-fPIC",
            f"-I{boost_root}",
            f"-I{os.path.join(boost_root, 'libs', 'atomic', 'src')}",
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_SYSTEM_NO_DEPRECATED",
            "-DBOOST_ATOMIC_NO_LIB",
            "-DBOOST_ATOMIC_SOURCE",
        ])

        # Atomic sources (libs/atomic/build/Jamfile.v2): lock_pool.cpp is the
        # only TU built on aarch64 Linux/OHOS — find_address_sse2/sse41 are
        # x86-only (select-arch-specific-sources), wait_on_address.cpp is
        # Windows-only (select-platform-specific-sources).
        atomic_src = [
            "lock_pool.cpp",
        ]
        self._compile_lib("atomic", os.path.join(boost_root, "libs/atomic/src"), atomic_src, cxx, ar, cxxflags)

        # ⚠️ 上游测试集成（规则 5）：b2 在 OHOS 不兼容（E068），改为手动编译
        # atomic 自带的上游测试源文件并真实运行（绕过 b2），统计通过率写入
        # 报告文件。测试基于上游 lightweight_test 框架（header-only），
        # 多线程部分用 std::thread（musl pthread 支持），IPC 测试用
        # boost::interprocess 的进程间原子量（基于共享内存 + 原子操作，
        # 无需额外编译库）。
        self._run_upstream_tests(boost_root, cxx, cxxflags)

    def _run_cmd(self, cmd, timeout, shell=False, env=None):
        """Run a command with a hard timeout, killing the whole process group
        on timeout so no orphaned child (e.g. clang++) keeps the CI worker busy.

        stdin is redirected to DEVNULL: if an upstream test tries to read from
        stdin it immediately gets EOF instead of hanging (interactive-test
        protection, per CI environment-issue guidance). `env` (when given) is
        used verbatim as the child environment (e.g. LD_LIBRARY_PATH pointing
        at the SDK libc++_shared.so).
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
        """编译并运行 Boost.Atomic 上游测试源文件（绕过 b2），统计通过率。

        测试文件来自 libs/atomic/test/（上游 Jamfile.v2 test-suite atomic），
        编译后直接运行可执行文件，以退出码 0 判定通过。报告写入
        build_folder/upstream-tests-report.txt。

        清单对齐上游 Jamfile（2026-09-06 人工审核实测基准，23 个测试目标）：
          - run 型 19 项：api/ref/ipc/wait/atomicity/ordering/lockfree/wait_fuzz
            （含 5 个 BOOST_ATOMIC_FORCE_FALLBACK 变体，独立测试目标，
            不折叠计数：fallback_atomic_api、fallback_atomic_ref_api、
            fallback_wait_api、fallback_wait_ref_api、fallback_wait_fuzz）
          - compile-fail 型 3 项（cf_arith_*，应编译失败）
          - compile 型 1 项（c_implicit_ctor，应编译成功）
        """
        lib_dir = self.build_folder
        # (源文件, 额外编译宏) —— FORCE_FALLBACK 变体按上游 Jamfile 注册
        # 为独立测试目标（同源文件 + BOOST_ATOMIC_FORCE_FALLBACK 宏重编）
        run_tests = [
            ("atomic_api.cpp", ""),
            ("atomic_ref_api.cpp", ""),
            ("atomic_api.cpp", "-DBOOST_ATOMIC_FORCE_FALLBACK"),
            ("atomic_ref_api.cpp", "-DBOOST_ATOMIC_FORCE_FALLBACK"),
            ("wait_api.cpp", ""),
            ("wait_ref_api.cpp", ""),
            ("wait_api.cpp", "-DBOOST_ATOMIC_FORCE_FALLBACK"),
            ("wait_ref_api.cpp", "-DBOOST_ATOMIC_FORCE_FALLBACK"),
            ("wait_fuzz.cpp", ""),
            ("wait_fuzz.cpp", "-DBOOST_ATOMIC_FORCE_FALLBACK"),
            ("ipc_atomic_api.cpp", ""),
            ("ipc_atomic_ref_api.cpp", ""),
            ("ipc_wait_api.cpp", ""),
            ("ipc_wait_ref_api.cpp", ""),
            ("atomicity.cpp", ""),
            ("atomicity_ref.cpp", ""),
            ("ordering.cpp", ""),
            ("ordering_ref.cpp", ""),
            ("lockfree.cpp", ""),
        ]
        compile_fail_tests = [
            "cf_arith_void_ptr.cpp",
            "cf_arith_func_ptr.cpp",
            "cf_arith_mem_ptr.cpp",
        ]
        compile_tests = [
            "c_implicit_ctor.cpp",
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

        def record(ok, line):
            nonlocal passed, failed
            report_lines.append(f"{'PASS' if ok else 'FAIL'} {line}")
            if ok:
                passed += 1
            else:
                failed += 1

        test_dir = os.path.join(boost_root, "libs", "atomic", "test")

        # 1) run 型：编译 + 运行（exit 0 判通过）
        #    FORCE_FALLBACK 变体用独立 exe 名与报告标签（fallback_ 前缀），
        #    与上游 Jamfile 的独立测试目标一一对应
        for src_name, extra_args in run_tests:
            src = os.path.join(test_dir, src_name)
            is_fallback = "FORCE_FALLBACK" in extra_args
            label = (f"fallback_{src_name}" if is_fallback else src_name)
            exe = os.path.join(lib_dir, f"test_{label.replace('.cpp', '')}")
            # Jamfile requirements: <threading>multi → -pthread；
            # variadic-macro 噪声抑制（上游 Jamfile 亦带此 cxxflags）
            cmd_compile = (f"{cxx} {cxxflags} -pthread -Wno-variadic-macros "
                           f"-Wno-c99-extensions {extra_args + ' ' if extra_args else ''}"
                           f"{src} -L{lib_dir} -lboost_atomic "
                           f"-o {exe}")
            ret_code, ret_out, ret_err = self._run_cmd(cmd_compile, timeout=300, shell=True)
            if ret_code != 0:
                record(False, f"{label} COMPILE_FAIL: "
                              f"{ret_err.splitlines()[-1] if ret_err.strip() else ''}")
                continue
            run_cmd = [exe]
            run_code, run_out, run_err = self._run_cmd(run_cmd, timeout=300, env=run_env)
            ok = run_code == 0
            detail = (run_out or run_err or "").strip().splitlines()
            record(ok, f"{label} rc={run_code}"
                       f"{f' ({detail[-1]})' if detail else ''}")

        # 2) compile-fail 型：应编译失败（rc != 0 才通过）
        for src_name in compile_fail_tests:
            src = os.path.join(test_dir, src_name)
            cmd = f"{cxx} {cxxflags} -fsyntax-only -Wno-variadic-macros {src}"
            ret_code, _, _ = self._run_cmd(cmd, timeout=120, shell=True)
            record(ret_code != 0, f"{src_name} (compile-fail expectation, rc={ret_code})")

        # 3) compile 型：应编译成功（rc == 0 通过）
        for src_name in compile_tests:
            src = os.path.join(test_dir, src_name)
            cmd = f"{cxx} {cxxflags} -fsyntax-only -Wno-variadic-macros {src}"
            ret_code, _, _ = self._run_cmd(cmd, timeout=120, shell=True)
            record(ret_code == 0, f"{src_name} (compile expectation, rc={ret_code})")

        report_lines.append(f"TOTAL {passed + failed}: {passed} passed / {failed} failed")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(f"上游测试报告: {report_path} ({passed}/{passed + failed} 通过)")
        for line in report_lines[-5:]:
            self.output.info(f"[upstream-tests] {line}")

    def package(self):
        # Install headers: copy entire boost/ include directory
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

        # Install compiled static libraries
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_*.a")):
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

    def package_info(self):
        # 拆分组件包使用独立的 CMake 包名 boost1.84-atomic，避免与
        # boost/1.84.0 元包的 cmake_file_name "Boost" 冲突（同一工程
        # 同时依赖两者时 CMakeDeps 生成文件不会互相覆盖）。
        self.cpp_info.set_property("cmake_file_name", "boost1.84-atomic")

        # Main "headers" component (always needed)
        self.cpp_info.components["boost1.84_atomic_headers"].includedirs = ["include"]
        # R8 合规：向所有消费者暴露 BOOST_SP_NO_PTHREAD_SETCANCELSTATE，
        # 使打过补丁的 sp_thread_sleep.hpp 跳过 pthread_setcancelstate
        # 路径（OHOS musl 无此 API），不依赖平台宏。atomic 自身源码不经过
        # 该路径，但复制了完整 boost 头文件树，下游若包含 boost/thread
        # 等头文件则需要此宏。
        self.cpp_info.components["boost1.84_atomic_headers"].defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        self.cpp_info.components["boost1.84_atomic_headers"].set_property("cmake_target_name", "boost1.84-atomic::headers")

        # Atomic（wait/notify API 依赖此编译库）
        self.cpp_info.components["boost1.84_atomic"].includedirs = []
        self.cpp_info.components["boost1.84_atomic"].libs = ["boost_atomic"]
        # Jamfile.v2 requires <threading>multi: pthread is needed by the
        # lock_pool fallback path on platforms without futex.
        self.cpp_info.components["boost1.84_atomic"].system_libs = ["pthread"]
        self.cpp_info.components["boost1.84_atomic"].requires = ["boost1.84_atomic_headers"]
        self.cpp_info.components["boost1.84_atomic"].set_property("cmake_target_name", "boost1.84-atomic::atomic")
