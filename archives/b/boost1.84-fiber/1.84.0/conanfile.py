#!/usr/bin/env python3
"""Conan recipe — boost1.84-fiber 1.84.0 (Boost.Fiber component package).

Boost 1.84.0 component split packaging for HarmonyOS PC (aarch64).
Boost.Fiber is a userland cooperative multitasking framework built on top of
Boost.Context (boost::context::fiber fcontext switching + waker-based
scheduling). This package follows the dependency-mode layout (task #6055):
it *requires* the already-published boost1.84-context/1.84.0 package and does
not recompile the fcontext assembler — the consumer links against
libboost_context.a from the context package.

The b2 build system is incompatible with OHOS (SHELL execution failure,
E068 error pattern), so the compiled library is built manually from sources
with the Conan-provided OHOS clang driver — same approach as boost/1.84.0,
boost1.84-context and boost1.84-thread precedents.

Source set — verified against upstream libs/fiber/build/Jamfile.v2
`lib boost_fiber` (16 translation units, NUMA library excluded):

    src/algo/algorithm.cpp, round_robin.cpp, shared_work.cpp,
    work_stealing.cpp, barrier.cpp, condition_variable.cpp, context.cpp,
    fiber.cpp, future.cpp, mutex.cpp, properties.cpp, recursive_mutex.cpp,
    recursive_timed_mutex.cpp, scheduler.cpp, timed_mutex.cpp, waker.cpp

Upstream defaults on OHOS aarch64 (both verified from the Jamfile):
  - NUMA (lib boost_fiber_numa): feature `numa` is optional and **off** by
    default (the `numa` conditional rule maps a missing <numa>on property to
    <build>no) — the boost_fiber_numa target is not built, matching b2.
  - segmented stacks: only wired for linux+gcc / clang with
    <segmented-stacks>on which is off by default; BOOST_USE_SEGMENTED_STACKS
    is never defined, matching b2 defaults on OHOS.

Library-TU compile defines (Jamfile project requirements):
  - BOOST_FIBERS_SOURCE (project <define>, library side)
  - BOOST_FIBER_SOURCE / BOOST_FIBERS_SOURCE (CMakeLists PRIVATE defines)
  - BOOST_ALL_NO_LIB (skip b2 auto-link pragmas, same as the meta-package)

CMakeDeps double-package layout (verified experimentally on conan 2.29.1):
when two packages in one dependency graph share cmake_file_name="Boost",
CMakeDeps silently keeps only ONE owner package's components (alphabetical:
boost1.84-context wins over boost1.84-fiber) — the loser's components are
dropped entirely. Therefore this package uses its own unique
cmake_file_name "boost1.84-fiber" (same pattern as boost1.84-log) and its
component references the context package via the fully-qualified component
name "boost1.84-context::boost_context", which CMakeDeps resolves across
packages (probe-verified: consumer find_package(boost1.84-fiber) +
target_link_libraries(... boost1.84-fiber::boost_fiber) links
libboost_context.a from the context package and runs).

Upstream test integration (rule 4/5): the upstream test targets registered
in libs/fiber/test/Jamfile.v2 are run directly with clang++ (bypassing b2,
same as boost1.84-thread #8554 / boost1.84-log precedents). All 32 test
sources (26 minimal + 6 mt extra) use the init_unit_test_suite pattern (no
own main()) and require boost_unit_test_framework, which is compiled as a
test-time dependency (19 TUs, never packaged). The 4 barrier/condition mt
tests additionally use boost::thread / boost::barrier, so a test-only
libboost_thread.a is compiled from libs/thread/src (5 TUs, same set as the
boost1.84-thread recipe, never packaged). See _run_upstream_tests.
"""
import glob
import os
import signal
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostFiberConan(ConanFile):
    name = "boost1.84-fiber"
    version = "1.84.0"
    description = "Boost.Fiber 1.84.0 组件包（libboost_fiber.a，依赖 boost1.84-context 的 fcontext 实现，鸿蒙 PC 适配）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 依赖模式（任务 #6055 要求）：fcontext 底层来自已发布的
        # boost1.84-context/1.84.0（fcontext 汇编 + posix stack_traits）
        self.requires("boost1.84-context/1.84.0")

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # 命令执行助手（超时杀进程组 + stdin EOF 保护，防孤儿进程拖死 CI；
    # 与 boost1.84-context / boost1.84-log 同款）
    # ------------------------------------------------------------------
    def _run_cmd(self, cmd, timeout, shell=False, env=None):
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

    def _find_libcxx_dir(self):
        """通过编译器自省定位 SDK libc++_shared.so 目录（无硬编码 SDK 版本
        路径，与 boost1.84-context / boost1.84-container 同款做法）。"""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        try:
            out = subprocess.check_output(
                [cxx, "-print-file-name=libc++_shared.so"], text=True).strip()
        except Exception as exc:  # noqa: BLE001
            self.output.warning(f"libc++_shared.so introspection failed: {exc}")
            return None
        if not out or out == "libc++_shared.so":
            return None
        return os.path.dirname(out)

    def _cxxflags(self, boost_root):
        if self.settings.build_type == "Debug":
            opt_flags = ["-O0", "-g"]
        else:
            opt_flags = ["-O2", "-DNDEBUG", "-g0"]
        return " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            *opt_flags,
            "-fPIC",
            # headers: boost 源树（fiber 头在顶层 boost/fiber/）
            f"-I{boost_root}",
            # libboost_context.a 的消费者侧不需要再定义 BOOST_CONTEXT_SOURCE
            "-DBOOST_ALL_NO_LIB",
            # 库自身 TU 编译宏（上游 Jamfile project requirements /
            # CMakeLists PRIVATE defines 双保险）
            "-DBOOST_FIBER_SOURCE",
            "-DBOOST_FIBERS_SOURCE",
            "-DBOOST_FIBERS_STATIC_LINK",
            # 静态链接形态的 context 消费者宏（coroutine 先例同款：
            # BOOST_CONTEXT_STATIC_LINK 防止 dllimport 变体符号）
            "-DBOOST_CONTEXT_STATIC_LINK",
            "-DBOOST_THREAD_DONT_USE_CHRONO=1",
            "-DBOOST_SYSTEM_NO_DEPRECATED",
            # R8 feature-detection 宏（OHOS musl 无 pthread_setcancelstate，
            # 与 boost/1.84.0 元包 0001 补丁同因，避免 smart_ptr 走该路径）
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
        ])

    def _compile_units(self, src_dir, src_files, obj_dir, cxx, cxxflags):
        """Compile source files into object files, return the object list."""
        objects = []
        os.makedirs(obj_dir, exist_ok=True)
        for src in src_files:
            src_path = os.path.join(src_dir, src)
            obj_name = src.replace("/", "_").replace(".cpp", ".o")
            obj_path = os.path.join(obj_dir, obj_name)
            ret, _, err = self._run_cmd(
                f"{cxx} {cxxflags} -c {src_path} -o {obj_path}",
                timeout=900, shell=True)
            if ret != 0:
                raise ConanException(
                    f"compile {src} failed rc={ret}: {err[-500:]}")
            objects.append(obj_path)
        return objects

    # 上游 libs/fiber/build/Jamfile.v2 `lib boost_fiber` 的 16 个 TU
    # （NUMA 库 boost_fiber_numa 默认 off，不打包）
    _FIBER_SOURCES = [
        "algo/algorithm.cpp",
        "algo/round_robin.cpp",
        "algo/shared_work.cpp",
        "algo/work_stealing.cpp",
        "barrier.cpp",
        "condition_variable.cpp",
        "context.cpp",
        "fiber.cpp",
        "future.cpp",
        "mutex.cpp",
        "properties.cpp",
        "recursive_mutex.cpp",
        "recursive_timed_mutex.cpp",
        "scheduler.cpp",
        "timed_mutex.cpp",
        "waker.cpp",
    ]

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")

        boost_root = self.source_folder
        cxxflags = self._cxxflags(boost_root)
        build = self.build_folder

        # ---- libboost_fiber.a：上游 Jamfile 16 TU 同源集合 ----
        fiber_objs = self._compile_units(
            os.path.join(boost_root, "libs", "fiber", "src"),
            self._FIBER_SOURCES,
            os.path.join(build, "obj_fiber"), cxx, cxxflags)
        lib_fiber = os.path.join(build, "libboost_fiber.a")
        ret, _, err = self._run_cmd(
            f"{ar} rcs {lib_fiber} {' '.join(fiber_objs)}",
            timeout=300, shell=True)
        if ret != 0:
            raise ConanException(
                f"archive libboost_fiber.a failed rc={ret}: {err[-500:]}")

        # ---- 上游测试集成（rule 4/5）：绕 b2 手动编译运行 ----
        self._run_upstream_tests(boost_root, cxx, cxxflags, ar)

    # ------------------------------------------------------------------
    # 上游测试（rule 4/5，b2 绕行——thread #8554 先例手法）
    # ------------------------------------------------------------------
    def _run_upstream_tests(self, boost_root, cxx, cxxflags, ar):
        """Compile and run the upstream boost.org/fiber test targets.

        Target inventory — libs/fiber/test/Jamfile.v2, verified against the
        official boost_1_84_0.tar.gz (rule-4 discipline: one target per
        [ run ] registration, no folding):
          - test-suite minimal: asm + native test-suites, each expanding the
            same 13 shared sources x post/dispatch variants = 26 [ run ]
            targets (the asm suite pins <context-impl>fcontext — our only
            built implementation; the native suite pins ucontext via the
            native-impl rule on non-windows, OHOS is not darwin/android so
            it stays <build>no-free... actually the rule forces
            <context-impl>ucontext which our context package does NOT ship;
            per the task handover the 26 minimal tests = 13 sources x 2
            launch policies are all run against the fcontext impl).
          - test-suite extra-asm/extra-native: 6 mt test sources
            (test_mutex_mt / test_condition_mt / test_future_mt, each
            x post/dispatch).
        All 32 test sources use init_unit_test_suite (no own main) and link
        boost_unit_test_framework (compiled here, 19 TUs, never packaged).
        The 4 barrier/condition mt tests use boost::thread + boost::barrier
        -> a test-only libboost_thread.a is compiled from libs/thread/src
        (5 TUs, the exact set of the boost1.84-thread recipe #8554, never
        packaged). test_future_mt_* use std::thread (pthread only).

        OHOS notes:
          - LD_LIBRARY_PATH prepended with the SDK libc++_shared.so dir
            (compiler introspection, no hardcoded SDK version); the musl
            loader only honors LD_LIBRARY_PATH when the process is started
            through a shell, so the run goes through `bash -c export ...`
            (same empirical conclusion as context/container).
          - fiber tests spin up scheduler dispatchers with real stacks; a
            300s per-test run timeout guards against scheduler livelocks
            without masking genuine failures.
        """
        build = self.build_folder
        test_dir = os.path.join(boost_root, "libs", "fiber", "test")
        ctx_pkg = self.dependencies["boost1.84-context"].package_folder
        ctx_lib = os.path.join(ctx_pkg, "lib", "libboost_context.a")

        # 1) boost_unit_test_framework — test-time dependency (19 TUs),
        #    never packaged (upstream test Jamfile links it project-wide).
        utf_src = [
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
        # 测试编译降档 -Os（context #CI-021 教训：纤维/协程模板实例化在
        # -O2 下链接内存峰值更高，低内存 worker linker signal 被杀；
        # 库本体保持 -O2 不变）
        test_flags = cxxflags.replace("-O2 -DNDEBUG -g0", "-Os -DNDEBUG -g0")
        # utf 自身编译不带 FIBERS 宏（纯净 TU），但保留
        # BOOST_SP_NO_PTHREAD_SETCANCELSTATE（OHOS musl 无该 API，
        # sp_thread_sleep 路径必须绕开——thread #8554 补丁同因）
        utf_flags = test_flags.replace(" -DBOOST_FIBER_SOURCE", "")
        utf_flags = utf_flags.replace(" -DBOOST_FIBERS_SOURCE", "")
        utf_flags = utf_flags.replace(" -DBOOST_FIBERS_STATIC_LINK", "")
        utf_objs = self._compile_units(
            os.path.join(boost_root, "libs", "test", "src"),
            utf_src, os.path.join(build, "obj_utf"), cxx, utf_flags)
        utf_lib = os.path.join(build, "libboost_unit_test_framework.a")
        ret, _, err = self._run_cmd(
            f"{ar} rcs {utf_lib} {' '.join(utf_objs)}", timeout=300, shell=True)
        if ret != 0:
            raise ConanException(f"archive utf failed rc={ret}: {err[-500:]}")

        # 2) libboost_thread.a — test-time dependency for the 4 barrier/
        #    condition mt tests (boost::thread + boost::barrier), never
        #    packaged. Same 5-TU set as boost1.84-thread #8554.
        thread_src = [
            "future.cpp", "tss_null.cpp", "pthread/once.cpp",
            "pthread/once_atomic.cpp", "pthread/thread.cpp",
        ]
        thread_flags = test_flags.replace(" -DBOOST_FIBER_SOURCE", "")
        thread_flags = thread_flags.replace(" -DBOOST_FIBERS_SOURCE", "")
        thread_flags = thread_flags.replace(" -DBOOST_FIBERS_STATIC_LINK", "")
        thread_flags = thread_flags.replace(
            " -DBOOST_THREAD_DONT_USE_CHRONO=1", "")
        thread_flags += " -DBOOST_THREAD_BUILDING_THE_LIB=1"
        thread_objs = self._compile_units(
            os.path.join(boost_root, "libs", "thread", "src"),
            thread_src, os.path.join(build, "obj_thread"), cxx, thread_flags)
        thread_lib = os.path.join(build, "libboost_thread.a")
        ret, _, err = self._run_cmd(
            f"{ar} rcs {thread_lib} {' '.join(thread_objs)}",
            timeout=300, shell=True)
        if ret != 0:
            raise ConanException(
                f"archive test-thread failed rc={ret}: {err[-500:]}")

        # 2b) libboost_chrono.a — test-time dependency for the 4 barrier/
        #     mt tests calling boost::this_thread::sleep_for(
        #     boost::chrono::milliseconds): BOOST_THREAD_USES_CHRONO drags
        #     in boost::chrono steady_clock symbols. 3 TUs with
        #     BOOST_CHRONO_SOURCE, never packaged (log #8609 precedent).
        chrono_src = ["chrono.cpp", "process_cpu_clocks.cpp", "thread_clock.cpp"]
        chrono_flags = test_flags.replace(" -DBOOST_FIBER_SOURCE", "")
        chrono_flags = chrono_flags.replace(" -DBOOST_FIBERS_SOURCE", "")
        chrono_flags = chrono_flags.replace(" -DBOOST_FIBERS_STATIC_LINK", "")
        chrono_flags += " -DBOOST_CHRONO_SOURCE"
        chrono_objs = self._compile_units(
            os.path.join(boost_root, "libs", "chrono", "src"),
            chrono_src, os.path.join(build, "obj_chrono"), cxx, chrono_flags)
        chrono_lib = os.path.join(build, "libboost_chrono.a")
        ret, _, err = self._run_cmd(
            f"{ar} rcs {chrono_lib} {' '.join(chrono_objs)}",
            timeout=300, shell=True)
        if ret != 0:
            raise ConanException(
                f"archive test-chrono failed rc={ret}: {err[-500:]}")

        # 3) 32 个测试源：26 minimal（13 源 x post/dispatch）+ 6 mt extra
        test_sources = sorted(glob.glob(os.path.join(test_dir, "*.cpp")))
        # 测试侧去掉 BOOST_THREAD_DONT_USE_CHRONO（mt 测试用
        # boost::this_thread::sleep_for(boost::chrono::milliseconds)，
        # 需 BOOST_THREAD_USES_CHRONO 默认开启；DONT_USE 是库 TU 侧的
        # 编译选项——log #8609 先例同款处理）
        test_flags = test_flags.replace(" -DBOOST_THREAD_DONT_USE_CHRONO=1", "")
        # mt 测试（boost::thread / std::thread 多线程宿主线程）需链接
        # libboost_thread.a（4 个 barrier/condition 源）+ -lpthread
        needs_thread = {
            "test_condition_mt_dispatch.cpp", "test_condition_mt_post.cpp",
            "test_mutex_mt_dispatch.cpp", "test_mutex_mt_post.cpp",
            "test_future_mt_dispatch.cpp", "test_future_mt_post.cpp",
        }
        libcxx_dir = self._find_libcxx_dir() if self.settings.os == "OHOS" else None

        report_lines = []
        passed, failed = 0, 0
        for src in test_sources:
            name = os.path.basename(src)
            exe = os.path.join(build, "ut_" + name.replace(".cpp", ""))
            libs = f"-L{build} -lboost_fiber {ctx_lib} {utf_lib} -lpthread"
            if name in needs_thread:
                libs = (
                    f"-L{build} -lboost_fiber {ctx_lib} {thread_lib} "
                    f"{chrono_lib} {utf_lib} -lpthread")
            cmd_compile = (
                f"{cxx} {test_flags} {src} {libs} -o {exe}")
            try:
                ret_code, _, ret_err = self._run_cmd(
                    cmd_compile, timeout=900, shell=True)
                if ret_code != 0:
                    tail = ret_err.splitlines()[-1] if ret_err.strip() else ""
                    report_lines.append(
                        f"COMPILE_FAIL {name}: {tail}")
                    failed += 1
                    continue
                if libcxx_dir:
                    run_cmd = (
                        f"export LD_LIBRARY_PATH='{libcxx_dir}:"
                        f"${{LD_LIBRARY_PATH:-}}'; '{exe}'")
                    run_code, _, _ = self._run_cmd(
                        run_cmd, timeout=300, shell=True)
                else:
                    run_code, _, _ = self._run_cmd([exe], timeout=300)
                ok = run_code == 0
                report_lines.append(
                    f"{'PASS' if ok else 'FAIL'} {name} rc={run_code}")
                if ok:
                    passed += 1
                else:
                    failed += 1
            except Exception as exc:  # noqa: BLE001 — 单测异常不中断整体
                report_lines.append(f"ERROR {name}: {exc}")
                failed += 1

        report_lines.append(
            f"TOTAL {passed + failed}: {passed} passed / {failed} failed")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(
            f"上游测试报告: {report_path} ({passed}/{passed + failed} 通过)")
        for line in report_lines:
            if line.startswith(("PASS", "FAIL", "COMPILE_FAIL", "ERROR")):
                self.output.info(f"[upstream-tests] {line}")
        if failed:
            raise ConanException(
                f"upstream fiber tests failed: {failed}/{passed + failed}")

    def package(self):
        # 完整 boost/ 头树与 context 包一致策略：Boost 库间头文件传递依赖
        # 强，部分头树会破坏传递 include（fiber 消费者 include
        # boost/fiber/all.hpp 会传递拉入 context/chrono 等大量头）
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE_1_0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 只打包 libboost_fiber.a（utf/thread 为测试期依赖，never packaged）
        libdir = os.path.join(self.package_folder, "lib")
        fiber_lib = os.path.join(self.build_folder, "libboost_fiber.a")
        copy(self, os.path.basename(fiber_lib), src=self.build_folder, dst=libdir)

    def package_id(self):
        pass

    def package_info(self):
        # 独立 cmake_file_name（避免与 boost1.84-context 的 "Boost" 撞名——
        # conan 2.29 实测同 cmake_file_name 时 CMakeDeps 静默丢弃字母序
        # 后者包的组件，fiber 组件会全部消失；boost1.84-log 先例同款独立名）
        self.cpp_info.set_property("cmake_file_name", "boost1.84-fiber")

        # 组件目标：boost1.84-fiber::boost_fiber（全限定名，log 先例风格）
        self.cpp_info.components["boost_fiber"].includedirs = []
        self.cpp_info.components["boost_fiber"].libs = ["boost_fiber"]
        # 跨包组件引用用全限定名（probe 实测：CMakeDeps 对
        # boost1.84-context::boost_context 生成聚合目标，链接期正确解析）
        self.cpp_info.components["boost_fiber"].requires = [
            "boost1.84-context::boost_context"]
        self.cpp_info.components["boost_fiber"].set_property(
            "cmake_target_name", "boost1.84-fiber::boost_fiber")

        # headers 组件：跟随本包 include 树（完整 boost 头树，与 context
        # 包内容一致；消费者一般同时装 context 包，头树重复无冲突）
        self.cpp_info.components["boost_headers"].includedirs = ["include"]
        self.cpp_info.components["boost_headers"].set_property(
            "cmake_target_name", "boost1.84-fiber::boost_headers")
        self.cpp_info.components["boost_fiber"].requires += ["boost_headers"]
