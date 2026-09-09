#!/usr/bin/env python3
"""Conan recipe — boost1.84-thread 1.84.0 (Boost.Thread standalone package).

boost1.84-thread 是 Debian 风格的 Boost.Thread 单库拆分包（对应
libboost-thread1.84-dev）：从 boost 1.84.0 源码树中独立裁剪编译
libboost_thread.a，仅打包 Boost.Thread 组件所需的头文件与库。

Boost b2 构建系统在 OHOS 上不兼容（E068 错误模式），本配方手动编译
libs/thread/src 下的源文件（future.cpp / tss_null.cpp / pthread 目录下
3 个文件）为静态库，并打包：
  - include/boost/thread/**（Thread 组件头文件及其传递依赖头文件集）
  - lib/libboost_thread.a
"""
import glob
import os
import signal
import subprocess

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class Boost184ThreadConan(ConanFile):
    name = "boost1.84-thread"
    version = "1.84.0"
    description = "Boost.Thread 1.84.0 单库拆分包（libboost_thread 静态库，鸿蒙 PC 适配）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""
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

    # ------------------------------------------------------------------
    # 上游源文件清单：
    # - libs/thread/src（对齐上游 libs/thread/build/Jamfile.v2 的
    #   thread_sources：pthread 后端 = future/tss_null/pthread/{once,once_atomic,thread}）
    # - libs/chrono/src 3 个文件：上游 usage-requirements 要求
    #   boost_thread 链接 boost_chrono（this_thread::sleep_for 等使用
    #   boost::chrono::steady_clock::now()）。单库拆分包自包含该依赖：
    #   chrono 的编译单元直接并入 libboost_thread.a。
    # ------------------------------------------------------------------
    THREAD_SOURCES = [
        "future.cpp",
        "tss_null.cpp",
        "pthread/once.cpp",
        "pthread/once_atomic.cpp",
        "pthread/thread.cpp",
    ]

    # boost_chrono 编译单元（libs/chrono/src，并入同一静态库以自包含）
    CHRONO_SOURCES = [
        "CHRONO::chrono.cpp",
        "CHRONO::process_cpu_clocks.cpp",
        "CHRONO::thread_clock.cpp",
    ]

    # Boost.Test 编译单元（libs/test/src，对齐 boost/1.90.0 配方的
    # unit_test_framework 源清单）：上游 thread 测试基于
    # boost/test/unit_test.hpp（BOOST_TEST_MODULE），链接期需要
    # libboost_unit_test_framework。测试阶段将其源文件与测试源一起
    # 编译进测试可执行文件（BOOST_TEST_ALTERNATIVE_INIT_API 静态模式）。
    _TEST_FRAMEWORK_SOURCES = [
        "compiler_log_formatter", "debug", "decorator", "execution_monitor",
        "framework", "junit_log_formatter", "plain_report_formatter",
        "progress_monitor", "results_collector", "results_reporter",
        "test_framework_init_observer", "test_tools", "test_tree",
        "unit_test_log", "unit_test_main", "unit_test_monitor",
        "unit_test_parameters", "xml_log_formatter", "xml_report_formatter",
    ]

    def _compile_lib(self, cxx, ar, cxxflags):
        """Compile thread + chrono sources and archive libboost_thread.a."""
        thread_src_dir = os.path.join(self.source_folder, "libs", "thread", "src")
        chrono_src_dir = os.path.join(self.source_folder, "libs", "chrono", "src")
        obj_dir = os.path.join(self.build_folder, "obj_thread")
        os.makedirs(obj_dir, exist_ok=True)
        objects = []
        for src in self.THREAD_SOURCES + self.CHRONO_SOURCES:
            base_dir = chrono_src_dir if src.startswith("CHRONO::") else thread_src_dir
            rel = src.split("::", 1)[1] if src.startswith("CHRONO::") else src
            src_path = os.path.join(base_dir, rel)
            obj_name = rel.replace("/", "_").replace(".cpp", ".o")
            obj_path = os.path.join(obj_dir, obj_name)
            self.run(f"{cxx} {cxxflags} -c {src_path} -o {obj_path}")
            objects.append(obj_path)
        # Boost.Test 编译单元供测试链接用（不进 libboost_thread.a——
        # 它是测试基础设施，不属于本包交付物；测试编译命令单独链接）。
        # 不定义 BOOST_TEST_ALTERNATIVE_INIT_API：上游 thread 测试用
        # BOOST_TEST_MODULE 自动生成 init_unit_test（标准模式），utf 的
        # unit_test_main.cpp 必须以同模式引用该符号（实测定义该宏会
        # undefined symbol: init_unit_test()）。
        testfw_dir = os.path.join(self.source_folder, "libs", "test", "src")
        utf_objects = []
        for name in self._TEST_FRAMEWORK_SOURCES:
            src_path = os.path.join(testfw_dir, name + ".cpp")
            obj_path = os.path.join(obj_dir, "utf_" + name + ".o")
            self.run(f"{cxx} {cxxflags} -c {src_path} -o {obj_path}")
            utf_objects.append(obj_path)
        self._utf_objects = utf_objects
        lib_path = os.path.join(self.build_folder, "libboost_thread.a")
        self.run(f"{ar} rcs {lib_path} {' '.join(objects)}")
        return lib_path

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")

        boost_root = self.source_folder
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
            # R8 compliance: skip pthread_setcancelstate (not available on
            # OHOS musl) via feature-detection macro consumed by patches/0001.
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
        ])

        self._compile_lib(cxx, ar, cxxflags)

        # 上游测试集成（规则 5）：b2 在 OHOS 不兼容（E068），无法运行 B2 测试
        # 目标。改为手动编译并运行 libs/thread/test 与 libs/thread/example 的
        # 代表性测试源文件（绕过 b2），以退出码 0 判定通过，统计通过率写入
        # 报告文件供 CI 与 PR 描述回填。
        self._run_upstream_tests(boost_root, cxx, cxxflags)

    def _run_cmd(self, cmd, timeout, shell=False):
        """Run a command with a hard timeout, killing the whole process group
        on timeout so no orphaned child keeps the CI worker busy.

        stdin is redirected to DEVNULL: if an upstream test tries to read
        from stdin it immediately gets EOF instead of hanging.
        """
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

    def _run_upstream_tests(self, boost_root, cxx, cxxflags):
        """编译并运行 Boost.Thread 上游测试子集，统计通过率。

        上游 libs/thread 共 469 个测试/示例源文件（46 example + 423 test，
        含 43 个编译期失败测试 _fail——用于验证错误代码不通过编译，不在
        运行时测试范围）。本配方选取覆盖 Thread 核心功能面的代表性子集：
        线程创建/移动/join、线程 ID、mutex 族、condition_variable、
        future/promise/async、once、tss、hardware_concurrency、example 示例。

        运行时环境：测试可执行文件按 OHOS clang 默认行为动态链接
        libc++_shared.so，该库不在系统默认搜索路径。通过
        `clang++ -print-file-name=libc++_shared.so` 自省定位 SDK libc++
        目录并注入 LD_LIBRARY_PATH（先例：boost/1.85.0 配方同款修复）。
        """
        lib_dir = self.build_folder
        test_run_env = os.environ.copy()
        libcxx_probe = self._run_cmd(
            f"{cxx} -print-file-name=libc++_shared.so", timeout=30, shell=True)
        libcxx_file = libcxx_probe[1].strip() if libcxx_probe[0] == 0 else ""
        if libcxx_file.startswith("/"):
            libcxx_dir = os.path.dirname(libcxx_file)
            if os.path.isdir(libcxx_dir):
                test_run_env["LD_LIBRARY_PATH"] = (
                    libcxx_dir + os.pathsep + test_run_env.get("LD_LIBRARY_PATH", ""))

        test_cases = [
            # (测试源文件相对 libs/thread 的路径, 断言数, 额外运行参数, 额外编译宏)
            ("test/test_thread.cpp", 30, "", ""),
            ("test/test_thread_id.cpp", 7, "", ""),
            ("test/test_thread_launching.cpp", 2, "", ""),
            ("test/test_thread_move.cpp", 15, "", ""),
            ("test/test_thread_move_return.cpp", 1, "", ""),
            ("test/test_thread_mf.cpp", 30, "", ""),
            ("test/test_thread_exit.cpp", 0, "", ""),
            ("test/test_hardware_concurrency.cpp", 2, "", ""),
            ("test/test_physical_concurrency.cpp", 2, "", ""),
            ("test/test_mutex.cpp", 39, "", ""),
            ("test/test_once.cpp", 9, "", ""),
            ("test/test_tss.cpp", 6, "", ""),
            ("test/test_condition.cpp", 0, "", ""),
            ("test/test_condition_notify_one.cpp", 0, "", ""),
            ("test/test_condition_notify_all.cpp", 0, "", ""),
            ("test/test_condition_timed_wait_times_out.cpp", 1, "", ""),
            ("test/test_futures.cpp", 13, "", ""),
            ("test/test_generic_locks.cpp", 11, "", ""),
            ("test/test_lock_concept.cpp", 20, "", ""),
            ("test/test_move_function.cpp", 1, "", ""),
            ("test/test_shared_mutex.cpp", 0, "", ""),
            ("test/test_shared_mutex_part_2.cpp", 0, "", ""),
            ("example/thread.cpp", 0, "", ""),
            ("example/mutex.cpp", 0, "", ""),
            ("example/condition.cpp", 0, "", ""),
            ("example/once.cpp", 0, "", ""),
            ("example/future_then.cpp", 0, "", ""),
            ("example/producer_consumer.cpp", 0, "", ""),
            ("example/thread_guard.cpp", 0, "", ""),
            ("example/scoped_thread.cpp", 0, "", ""),
        ]
        report_lines = []
        passed, failed = 0, 0
        for src_rel, asserts, extra_args, extra_defines in test_cases:
            src = os.path.join(boost_root, "libs", "thread", src_rel)
            exe = os.path.join(lib_dir, "test_" + os.path.basename(src_rel).replace(".cpp", ""))
            define_flags = (f"-D{extra_defines} " if extra_defines else "")
            # 上游测试分两类（按源码内容探测，不以目录为判据——
            # test_thread_mf.cpp 在 test/ 下但自带 main()）：
            # - 含 BOOST_TEST_MODULE：基于 Boost.Test，链接测试基础设施
            #   对象（self._utf_objects，build 阶段已编译）；
            # - 自带 main()：不链接 utf（否则 duplicate symbol: main）。
            needs_utf = False
            try:
                with open(src, encoding="utf-8", errors="ignore") as fh:
                    needs_utf = "BOOST_TEST_MODULE" in fh.read()
            except OSError:
                pass
            utf_objs = " ".join(getattr(self, "_utf_objects", [])) if needs_utf else ""
            cmd_compile = (f"{cxx} {cxxflags} -DBOOST_TEST_NO_LIB {define_flags}"
                           f"{src} -L{lib_dir} -lboost_thread -lpthread "
                           f"{utf_objs} -o {exe}")
            try:
                ret_code, ret_out, ret_err = self._run_cmd(cmd_compile, timeout=300, shell=True)
                if ret_code != 0:
                    last_err = ret_err.splitlines()[-1] if ret_err else ""
                    report_lines.append(f"COMPILE_FAIL {src_rel}: {last_err}")
                    failed += 1
                    continue
                run_cmd = [exe] + (extra_args.split() if extra_args else [])
                run_proc = subprocess.Popen(
                    run_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, stdin=subprocess.DEVNULL, env=test_run_env)
                try:
                    run_out, run_err = run_proc.communicate(timeout=120)
                    run_code = run_proc.returncode
                except subprocess.TimeoutExpired:
                    run_proc.kill()
                    run_out, run_err = run_proc.communicate()
                    run_code = -1
                ok = run_code == 0
                report_lines.append(f"{'PASS' if ok else 'FAIL'} {src_rel} (断言≈{asserts}) rc={run_code}")
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
        for line in report_lines[-8:]:
            self.output.info(f"[upstream-tests] {line}")

    # ------------------------------------------------------------------
    # Thread 组件头文件传递依赖集：clang++ -E -H 预处理探测
    # #include <boost/thread.hpp> 实际展开的全部 boost 顶级头/目录
    # （51 项，比上游 CMake target_link_libraries 组件清单更精确——
    # 后者是逻辑组件依赖，前者是物理 include 依赖）
    # ------------------------------------------------------------------
    _HEADER_DEPS = [
        # 目录形式依赖
        "assert", "atomic", "bind", "chrono", "config", "container_hash",
        "core", "date_time", "describe", "detail", "exception", "function",
        "functional", "io", "move", "mp11", "mpl", "numeric", "optional",
        "predef", "preprocessor", "ratio", "smart_ptr", "static_assert",
        "system", "thread", "throw_exception", "tuple", "type", "type_traits",
        "utility", "winapi", "iterator", "container", "intrusive", "integer",
        "lexical_cast",
        # 单文件形式依赖（*.hpp）
        "cstdint", "current_function", "enable_shared_from_this",
        "exception_ptr", "function_equal", "get_pointer", "integer_traits",
        "io_fwd", "is_placeholder", "limits", "make_shared", "mem_fn",
        "memory_order", "none", "none_t", "operators", "scoped_array",
        "shared_ptr", "visit_each", "version", "weak_ptr",
    ]

    def package(self):
        # 头文件打包策略：完整复制 boost/ 头文件树。
        # 为什么整体打包而非仅 Thread 组件：Thread 的头文件传递依赖集
        # 跨 30+ 个顶级模块（date_time/chrono/functional/...），且包含
        # .ipp/.inc 等非 .hpp 实现文件，逐文件裁剪极易遗漏（实测
        # gregorian_calendar.ipp 缺失）。所有 boost1.84-* 拆分包同源
        # 同版本头文件树（boost 1.84.0 tarball），安装内容完全一致，
        # 与 archives/b/boost/1.84.0 本体先例的做法一致。
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

        # 库文件
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_*.a")):
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

        # 许可文件
        copy(self, "LICENSE_1_0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")
        self.cpp_info.set_property("pkg_config_name", "boost_thread")

        # Thread 组件：Debian libboost-thread1.84-dev 等价物
        comp = self.cpp_info.components["boost_thread"]
        comp.libs = ["boost_thread"]
        comp.includedirs = ["include"]
        comp.libdirs = ["lib"]
        comp.set_property("cmake_target_name", "Boost::thread")
        comp.set_property("pkg_config_name", "libboost_thread")
        comp.defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        comp.system_libs = ["pthread"]
        # libboost_thread 在上游链接 boost_chrono + boost_system +
        # boost_atomic（Boost.Thread 文档依赖集）；本包为静态库自包含，
        # chrono/system 于 1.84 为 header-only 使用形态，无额外库依赖。
        comp.requires = []
