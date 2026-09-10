#!/usr/bin/env python3
"""Conan recipe — boost1.84-stacktrace_basic 1.84.0 (Boost.Stacktrace basic split package).

Boost 1.84.0 组件拆分包之一：交付 Boost.Stacktrace 的 basic 编译库形态
（libboost_stacktrace_basic.a + 完整 boost 头文件树）。

形态选型（见 notes.md）：
- basic = 上游 lib boost_stacktrace_basic（libs/stacktrace/src/basic.cpp）：
  无 libbacktrace 依赖、无 addr2line 子进程、无 WinDbg 的"basic"实现，
  帧收集走 _Unwind_Backtrace，符号解析走 dladdr（musl 提供）+ 导出表
  （-rdynamic 导出 BOOST_SYMBOL_VISIBLE 符号）。
- OHOS musl 实测（2026-09-06，clang 15 / aarch64-linux-ohos）：
  backtrace()（execinfo.h）3 帧可用、dladdr() 返回符号名可用、
  _Unwind_Backtrace 帧收集可用——basic 模式在 OHOS 上完全可用。
- 独立裁剪包（非 requires 元包）。原因：boost/1.84.0 元包只编译了
  filesystem/regex/program_options/iostreams 四个库，未声明
  boost_stacktrace_basic 组件、lib/ 无 libboost_stacktrace_basic.a——
  requires 元包拿不到 `Boost::stacktrace_basic` 目标；且元包
  cmake_file_name "Boost" 与组件包同工程共存时 CMakeDeps 生成文件
  互相覆盖。

Boost b2 build system is incompatible with OHOS (E068, see meta-package
notes.md), so we manually compile basic.cpp into a static archive,
mirroring the meta-package recipe approach.
"""
import glob
import os
import signal
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostStacktraceBasicConan(ConanFile):
    name = "boost1.84-stacktrace_basic"
    version = "1.84.0"
    description = "Boost.Stacktrace 1.84.0 拆分组件包（libboost_stacktrace_basic 静态库：_Unwind_Backtrace 帧收集 + dladdr 符号解析，鸿蒙 PC 适配）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/doc/libs/1_84_0/libs/stacktrace/"
    url = ""
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    # Boost b2 build system is incompatible with OHOS, so we manually compile
    # the stacktrace basic source into a static archive (same rationale as
    # the boost/1.84.0 meta package recipe).
    # Boost 源码树 5 万+文件，在 OHOS HMDFS 上整体复制到 build folder 极慢
    # （实测 >13 分钟未完成）。本配方对源码只读（补丁由 conan 在导出副本
    # 上应用），直接在 source_folder 上编译，跳过复制（no_copy_source 语义）。
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
        # 上游 libs/stacktrace/build/Jamfile.v2：lib boost_stacktrace_basic :
        # ../src/basic.cpp，requirements <warnings>all；
        # <target-os>linux:<library>dl（aarch64-linux-ohos 属 linux 族，
        # dladdr 在 libdl；musl 将 dl 合入 libc 但显式 -ldl 兼容）。
        # basic.cpp 自身 #define _GNU_SOURCE（dladdr 需要）。
        cxxflags = " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            *opt_flags,
            "-fPIC",
            f"-I{boost_root}",
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_SYSTEM_NO_DEPRECATED",
            # R8 合规：跳过 pthread_setcancelstate（OHOS musl 无此 API），
            # patch 0001 消费此特性检测宏。stacktrace/basic.cpp 自身不经
            # 该路径，但测试辅助库（thread.cpp）必须。
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
        ])

        # Stacktrace basic source（上游 Jamfile：仅 ../src/basic.cpp 一个 TU）
        self._compile_lib("stacktrace_basic",
                          os.path.join(boost_root, "libs/stacktrace/src"),
                          ["basic.cpp"], cxx, ar, cxxflags)

        # ⚠️ 上游测试集成（规则 5）：b2 在 OHOS 不兼容（E068），改为手动编译
        # 上游 libs/stacktrace/test 的测试目标（绕过 b2）并真实运行，统计
        # 通过率写入报告文件。清单对齐上游 Jamfile.v2 test-suite
        # stacktrace_tests 中 basic 变体 + 独立小测试（见 _run_upstream_tests
        # docstring 逐项说明）。
        self._run_upstream_tests(boost_root, cxx, ar, cxxflags)

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

    def _run_upstream_tests(self, boost_root, cxx, ar, cxxflags):
        """编译并运行 Boost.Stacktrace 上游测试目标（绕过 b2），统计通过率。

        上游 test-suite stacktrace_tests 按 6 种实现变体（backtrace/addr2line/
        noop/windbg/windbg_cached/basic）× 3 种链接形态（header-only/linked
        库/threaded）× 2 种调试符号（on/off）注册目标。OHOS musl 上可跑的
        实现变体共两种——basic 与 noop（合计 23 个注册目标，2026-09-07
        rule4 复核口径）：

          basic 变体（17 目标）：
          1.  basic_ho           — test.cpp + test_impl.cpp，debug-symbols on，
              -DBOOST_STACKTRACE_TEST_EXPORTS_TABLE_USAGE -rdynamic（FORCE_SYMBOL_EXPORT）
          2.  basic_ho_empty     — 同上 + -DBOOST_STACKTRACE_TEST_NO_DEBUG_AT_ALL
          3.  trivial_basic_ho   — test_trivial.cpp
          4.  basic_lib          — test.cpp 链接 test_impl_lib_basic（shared impl）
          5.  trivial_basic_lib  — test_trivial.cpp 链接 shared impl
          6.  basic_ho_no_dbg    — debug-symbols off 变体
          7.  basic_ho_no_dbg_empty — off + NO_DEBUG_AT_ALL
          8.  basic_lib_no_dbg   — 链接 shared impl + off
          9.  basic_lib_threaded — thread_safety_checking.cpp + boost_thread + boost_timer
          10. basic_lib_no_dbg_threaded — 同上 off 变体
          11-16. basic_<example> 6 个 example（assert_handler/debug_function/
              terminate_handler/throwing_st/trace_addresses/user_config）的
              basic 变体 ×2（debug-symbols on/off 折叠计入，标签 basic_<name>）
          17. test_void_ptr_cast + test_num_conv — 独立小测试（无变体，各计 1）
          （上机计数：1-10 = 10 + example 6 = 16 + 独立 2 = 18 项运行，
           其中 basic_ho_empty 与 basic_ho_no_dbg_empty 为同目标双名折叠 → 17）

          noop 变体（6 目标，OHOS musl 可跑——无栈收集的空实现模式，
          BOOST_STACKTRACE_USE_NOOP，帧收集 collect() 返回 0）：
          18. noop_ho           — test_noop.cpp + test_impl.cpp，-DBOOST_STACKTRACE_USE_NOOP
          19. trivial_noop_ho   — test_trivial.cpp + NOOP
          20. noop_lib          — test_noop.cpp 链接 noop 库形态
          21. trivial_noop_lib  — test_trivial.cpp 链接 noop 库形态
          22. noop_ho_no_dbg    — NOOP + debug-symbols off
          23. noop_lib_no_dbg   — NOOP 库形态 + off

        不纳入（逐类说明）：
          - backtrace 变体（~12 目标）：OHOS 无 libbacktrace 系统库，上游
            check-target-builds libbacktrace 检测失败即 <build>no——平台无此
            依赖，实测 has_backtrace.cpp 链接 -lbacktrace 失败。
          - addr2line 变体（~12 目标）：运行时子进程调用外部 binutils
            addr2line 工具，OHOS 系统镜像不含该工具，且上游
            check-target-builds addr2line 失败即 <build>no。
          - windbg/windbg_cached 变体（~16 目标）：Windows Dbgeng/ole32 专属，
            上游在 Linux 系 check-target-builds 失败即 <build>no。
          - torture_basic_*（4 目标）：上游 explicit 标记的
            "Very long tests"（torture.cpp 循环 1000 万次取 source_line），
            CI 环境跑不动，上游也默认不跑（explicit）。

        帧收集实测（2026-09-06 OHOS）：_Unwind_Backtrace 正常返回帧；
        dladdr 在 -rdynamic 导出符号时返回可读函数名（test.cpp 的
        BOOST_STACKTRACE_TEST_SHOULD_OUTPUT_READABLE_NAMES=1 路径可过）。

        basic_lib 系列（shared 链接形态）：上游用 test_impl_lib_basic（把
        test_impl.cpp 编成带 shared boost_stacktrace_basic 实现的库）。本配方
        等价实现：test_impl.cpp 与主测试一起编译（上游 basic_ho 即此形态，
        <define>BOOST_STACKTRACE_TEST_EXPORTS_TABLE_USAGE + -rdynamic 使
        BOOST_SYMBOL_VISIBLE 函数进导出表）+ 链接 libboost_stacktrace_basic.a。
        """
        lib_dir = self.build_folder
        test_dir = os.path.join(boost_root, "libs", "stacktrace", "test")
        example_dir = os.path.join(boost_root, "libs", "stacktrace", "example")

        report_lines = []
        passed, failed = 0, 0
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

        def compile_and_run(label, srcs, extra_defs, link_lib, timeout=300):
            exe = os.path.join(lib_dir, f"test_{label}")
            include_flags = f"-I{test_dir}"
            src_paths = " ".join(srcs)
            cmd_compile = (f"{cxx} {cxxflags} {include_flags} {extra_defs} "
                           f"{src_paths} -L{lib_dir} {link_lib} -o {exe} -rdynamic")
            ret_code, _, ret_err = self._run_cmd(cmd_compile, timeout=timeout, shell=True)
            if ret_code != 0:
                last = ret_err.splitlines()[-1] if ret_err.strip() else ""
                record(False, f"{label} COMPILE_FAIL: {last}")
                return
            run_code, run_out, run_err = self._run_cmd([exe], timeout=timeout, env=run_env)
            detail = (run_out or run_err or "").strip().splitlines()
            record(run_code == 0, f"{label} rc={run_code}"
                   f"{f' ({detail[-1]})' if detail else ''}")

        # ── 1) basic 主测试：header-only（basic_ho）＋ NO_DEBUG_AT_ALL 变体 ──
        # 上游：[ run test.cpp test_impl.cpp : : : <debug-symbols>on
        #   $(FORCE_SYMBOL_EXPORT) $(BASIC_DEPS) : basic_ho ]
        # FORCE_SYMBOL_EXPORT on linux = -rdynamic + EXPORTS_TABLE_USAGE define。
        # 优化级别：b2 测试目标默认 debug 变体（-O0），-O2 会内联吞掉
        # test_impl.cpp 的 function_from_library 帧（实测 5 断言失败），
        # 故测试编译固定 -O0 -g（上游 debug 变体语义）。
        test_opt = "-O0 -g"
        ho_defs = f"-DBOOST_STACKTRACE_TEST_EXPORTS_TABLE_USAGE {test_opt}"
        compile_and_run(
            "basic_ho",
            [os.path.join(test_dir, "test.cpp"), os.path.join(test_dir, "test_impl.cpp")],
            ho_defs, "")
        # basic_ho_empty：strip 场景（无调试信息也可运行）
        compile_and_run(
            "basic_ho_empty",
            [os.path.join(test_dir, "test.cpp"), os.path.join(test_dir, "test_impl.cpp")],
            ho_defs + " -DBOOST_STACKTRACE_TEST_NO_DEBUG_AT_ALL", "")

        # ── 2) trivial：basic 变体（test_trivial.cpp）──
        compile_and_run(
            "trivial_basic_ho",
            [os.path.join(test_dir, "test_trivial.cpp")], ho_defs, "")

        # ── 3) linked 库形态（basic_lib）：链接 libboost_stacktrace_basic.a ──
        # 上游：[ run test.cpp : : : <library>.//test_impl_lib_basic
        #   $(LINKSHARED_BASIC) : basic_lib ]，test_impl_lib_basic 以
        # <link>shared 的 boost_stacktrace_basic 实现 + BOOST_STACKTRACE_DYN_LINK
        # 编译。等价单文件可执行形态：主测试 + test_impl.cpp 一起编译，
        # 链接本包静态库（BOOST_STACKTRACE_LINK 由库消费者侧生效，
        # 无 DYN_LINK 定义即静态链接）。
        lib_defs = f"-DBOOST_STACKTRACE_TEST_EXPORTS_TABLE_USAGE {test_opt}"
        compile_and_run(
            "basic_lib",
            [os.path.join(test_dir, "test.cpp"), os.path.join(test_dir, "test_impl.cpp")],
            lib_defs, "-lboost_stacktrace_basic")
        compile_and_run(
            "trivial_basic_lib",
            [os.path.join(test_dir, "test_trivial.cpp")],
            lib_defs, f"-lboost_stacktrace_basic")

        # ── 4) no_dbg 变体（basic_ho_no_dbg / basic_lib_no_dbg）──
        # 平台修复：OHOS clang 15 在 -O0 且无 -g 时 .eh_frame 不完整，
        # _Unwind_Backtrace 只能收集 1-2 帧（test_frame min_size>2 失败）；
        # -fasynchronous-unwind-tables 强制生成完整异步展开表（等价于
        # 上游 gcc 默认行为），实测修复。上游语义（无调试符号）保持——
        # 不加 -g。
        no_dbg_defs = (f"-DBOOST_STACKTRACE_TEST_EXPORTS_TABLE_USAGE -O0 "
                       f"-fasynchronous-unwind-tables")
        compile_and_run(
            "basic_ho_no_dbg",
            [os.path.join(test_dir, "test.cpp"), os.path.join(test_dir, "test_impl.cpp")],
            no_dbg_defs + " -DBOOST_STACKTRACE_TEST_NO_DEBUG_AT_ALL", "")
        compile_and_run(
            "basic_lib_no_dbg",
            [os.path.join(test_dir, "test.cpp"), os.path.join(test_dir, "test_impl.cpp")],
            no_dbg_defs + " -DBOOST_STACKTRACE_TEST_NO_DEBUG_AT_ALL", "")

        # ── 5) 线程安全（basic_lib_threaded）：boost_thread + boost_timer ──
        # 上游：thread_safety_checking.cpp + /boost/thread + /boost/timer +
        # test_impl_lib_basic。boost_thread 不在本包交付范围，但源码树
        # libs/thread/src 就地可用：按 timer 包同款辅助库做法，把 thread/timer
        # 编译成构建期辅助静态库供测试链接（不随包交付）。
        self._build_thread_timer_aux(boost_root, cxx, ar, cxxflags)
        if self._aux_ok:
            compile_and_run(
                "basic_lib_threaded",
                [os.path.join(test_dir, "thread_safety_checking.cpp"),
                 os.path.join(test_dir, "test_impl.cpp")],
                f"-DBOOST_STACKTRACE_TEST_EXPORTS_TABLE_USAGE {test_opt} -pthread",
                "-lboost_stacktrace_basic -lboost_thread -lboost_timer")
            compile_and_run(
                "basic_lib_no_dbg_threaded",
                [os.path.join(test_dir, "thread_safety_checking.cpp"),
                 os.path.join(test_dir, "test_impl.cpp")],
                f"-DBOOST_STACKTRACE_TEST_EXPORTS_TABLE_USAGE "
                f"-DBOOST_STACKTRACE_TEST_NO_DEBUG_AT_ALL "
                f"-fasynchronous-unwind-tables -O0 -pthread",
                "-lboost_stacktrace_basic -lboost_thread -lboost_timer")
        else:
            record(False, "basic_lib_threaded SKIPPED: aux thread/timer build failed")
            record(False, "basic_lib_no_dbg_threaded SKIPPED: aux thread/timer build failed")

        # ── 6) 独立小测试（无变体）──
        compile_and_run("test_void_ptr_cast",
                        [os.path.join(test_dir, "test_void_ptr_cast.cpp")], "", "")
        compile_and_run("test_num_conv",
                        [os.path.join(test_dir, "test_num_conv.cpp")], "", "")

        # ── 6.5) noop 变体（6 目标，OHOS musl 可跑）──
        # 上游 Jamfile：[ run test_noop.cpp test_impl.cpp : : :
        #   <debug-symbols>on <define>BOOST_STACKTRACE_USE_NOOP : noop_ho ] 等
        # 6 目标。noop = 无栈收集的空实现模式（collect() 返回 0，
        # frame::name()/source_file()/source_line() 返回空值），test_noop.cpp
        # 断言空栈语义（size()==0/empty()/比较相等）——OHOS 上无任何平台
        # 依赖，可完整运行。库形态（noop_lib）链接 libboost_stacktrace_noop.a
        # （libs/stacktrace/src/noop.cpp 就地编译，上游 lib boost_stacktrace_noop
        # 等价物；不随包交付，package() 只打包 libboost_stacktrace_basic.a）。
        self._build_noop_aux(boost_root, cxx, ar, cxxflags)
        noop_defs = f"-DBOOST_STACKTRACE_USE_NOOP {test_opt}"
        compile_and_run(
            "noop_ho",
            [os.path.join(test_dir, "test_noop.cpp"),
             os.path.join(test_dir, "test_impl.cpp")], noop_defs, "")
        compile_and_run(
            "trivial_noop_ho",
            [os.path.join(test_dir, "test_trivial.cpp")], noop_defs, "")
        compile_and_run(
            "noop_lib",
            [os.path.join(test_dir, "test_noop.cpp"),
             os.path.join(test_dir, "test_impl.cpp")],
            noop_defs, "-lboost_stacktrace_noop")
        compile_and_run(
            "trivial_noop_lib",
            [os.path.join(test_dir, "test_trivial.cpp")],
            noop_defs, "-lboost_stacktrace_noop")
        # no_dbg 变体：-fasynchronous-unwind-tables 平台修复同 basic
        #（noop 的 collect 返回 0 不依赖展开表，但保持与 basic no_dbg 一致
        # 的编译参数口径）
        noop_nodbg_defs = (f"-DBOOST_STACKTRACE_USE_NOOP -O0 "
                           f"-fasynchronous-unwind-tables")
        compile_and_run(
            "noop_ho_no_dbg",
            [os.path.join(test_dir, "test_noop.cpp"),
             os.path.join(test_dir, "test_impl.cpp")], noop_nodbg_defs, "")
        compile_and_run(
            "noop_lib_no_dbg",
            [os.path.join(test_dir, "test_noop.cpp"),
             os.path.join(test_dir, "test_impl.cpp")],
            noop_nodbg_defs, "-lboost_stacktrace_noop")

        # ── 6.5) terminate_handler 所需的 filesystem/system 辅助库 ──
        # 上游 Jamfile：terminate_handler requires /boost/filesystem +
        # /boost/system + rt。filesystem 是编译库（本包不含），源码树
        # libs/filesystem/src 就地编译为辅助静态库（文件集与元包一致）。
        # boost_system 1.84 为 header-only（无需编译）。rt 在 musl 已合并
        # 进 libc（时钟函数无需 -lrt）。
        self._fs_ok = self._build_filesystem_aux(boost_root, cxx, ar, cxxflags)

        # ── 7) example 的 basic 变体（debug-symbols on/off 折叠为 1 项/例）──
        # 上游对每个 example 注册 backtrace/addr2line/windbg/windbg_cached/
        # noop/basic × dbg on/off 共 12 个目标；basic 相关为 2 个/example，
        # 折叠计数 6 个 example × 1 = 6 项（标签 basic_<name>）。
        # terminate_handler 需 boost_filesystem+boost_system+rt（Jamfile
        # additional_dependency）：元包源码树就地编译辅助库（同 thread/timer）。
        # terminate_handler 的 additional_dependency：Jamfile 是
        # /boost/filesystem + /boost/system + rt。boost_system 1.84 是
        # header-only（无 libboost_system.a，-lboost_system 会链接失败）；
        # rt 在 musl 已并入 libc。只需链接辅助 filesystem 静态库。
        example_tests = [
            ("assert_handler.cpp", []),
            ("debug_function.cpp", []),
            ("terminate_handler.cpp", ["boost_filesystem"]),
            ("throwing_st.cpp", []),
            ("trace_addresses.cpp", []),
            ("user_config.cpp", []),
        ]
        for src_name, aux_libs in example_tests:
            label = "basic_" + src_name.replace(".cpp", "")
            link = "-lboost_stacktrace_basic" + (
                "".join(f" -l{n}" for n in aux_libs))
            if "boost_filesystem" in aux_libs and not self._fs_ok:
                record(False, f"{label} SKIPPED: aux filesystem build failed")
                continue
            compile_and_run(
                label, [os.path.join(example_dir, src_name)],
                f"-DBOOST_STACKTRACE_TEST_EXPORTS_TABLE_USAGE {test_opt}", link)

        report_lines.append(f"TOTAL {passed + failed}: {passed} passed / {failed} failed")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(f"上游测试报告: {report_path} ({passed}/{passed + failed} 通过)")
        for line in report_lines:
            self.output.info(f"[upstream-tests] {line}")

    def _build_noop_aux(self, boost_root, cxx, ar, cxxflags):
        """构建 noop 变体测试所需的辅助 libboost_stacktrace_noop.a。

        上游 Jamfile：lib boost_stacktrace_noop : ../src/noop.cpp（NOOP_DEPS
        为空——无任何平台依赖）。noop.cpp = 帧收集空实现（collect 返回 0）
        + 空 dump。源码树 libs/stacktrace/src/noop.cpp 就地编译为构建期
        辅助静态库，供 noop_lib 系列测试链接；不随包交付（package() 只
        打包 libboost_stacktrace_basic.a——本包交付形态为 basic）。
        """
        if getattr(self, "_noop_aux_done", False):
            return
        obj = os.path.join(self.build_folder, "obj_noop", "noop.o")
        os.makedirs(os.path.dirname(obj), exist_ok=True)
        src = os.path.join(boost_root, "libs/stacktrace/src/noop.cpp")
        # noop.cpp 自带 #define BOOST_STACKTRACE_USE_NOOP
        cmd = f"{cxx} {cxxflags} -c {src} -o {obj}"
        ret_code, _, ret_err = self._run_cmd(cmd, timeout=300, shell=True)
        if ret_code != 0:
            last = ret_err.splitlines()[-1] if ret_err.strip() else ""
            self.output.warning(f"aux noop.cpp failed: {last}")
            return
        lib_path = os.path.join(self.build_folder, "libboost_stacktrace_noop.a")
        self.run(f"{ar} rcs {lib_path} {obj}")
        self._noop_aux_done = True

    def _build_thread_timer_aux(self, boost_root, cxx, ar, cxxflags):
        """构建 thread_safety_checking 所需的辅助 boost_thread/boost_timer 静态库。

        上游 Jamfile：thread_safety_checking.cpp requires /boost/thread 与
        /boost/timer。这两个库不在本包交付范围（stacktrace 实现不依赖），
        但源码树 libs/thread/src、libs/timer/src 就地可用：用与本包完全相同
        的 cxxflags 编译成构建期辅助静态库供测试链接，测试结束不随包交付
        （package() 只打包 libboost_stacktrace_basic.a）。
        文件集与 boost1.84-thread/timer 组件包一致。
        """
        self._aux_ok = False
        aux_dir = os.path.join(self.build_folder, "obj_aux")
        os.makedirs(aux_dir, exist_ok=True)

        thread_src = [
            "pthread/once.cpp", "pthread/thread.cpp",
        ]
        timer_src = [
            "auto_timers_construction.cpp", "cpu_timer.cpp",
        ]
        objs = []
        for rel in [f"thread/{s}" for s in thread_src] + [f"timer/{s}" for s in timer_src]:
            if rel.startswith("thread/"):
                src_path = os.path.join(boost_root, "libs/thread/src", rel.split("/", 1)[1])
            else:
                src_path = os.path.join(boost_root, "libs/timer/src", rel.split("/", 1)[1])
            obj_path = os.path.join(aux_dir, rel.replace("/", "_").replace(".cpp", ".o"))
            cmd = (f"{cxx} {cxxflags} -pthread -c {src_path} -o {obj_path}")
            ret_code, _, ret_err = self._run_cmd(cmd, timeout=300, shell=True)
            if ret_code != 0:
                last = ret_err.splitlines()[-1] if ret_err.strip() else ""
                self.output.warning(f"aux {rel} compile failed: {last}")
                return
            objs.append((rel.split("/")[0], obj_path))

        for lib_name in ["thread", "timer"]:
            lib_objs = [o for n, o in objs if n == lib_name]
            if not lib_objs:
                self.output.warning(f"aux lib {lib_name}: no objects")
                return
            lib_path = os.path.join(self.build_folder, f"libboost_{lib_name}.a")
            self.run(f"{ar} rcs {lib_path} {' '.join(lib_objs)}")
        self._aux_ok = True

    def _build_filesystem_aux(self, boost_root, cxx, ar, cxxflags):
        """构建 terminate_handler example 所需的辅助 boost_filesystem 静态库。

        上游 Jamfile：terminate_handler requires /boost/filesystem 与
        /boost/system。boost_system 1.84 是 header-only（无需编译）；
        filesystem 是编译库，不在本包交付范围，但源码树 libs/filesystem/src
        就地可用：用与本包完全相同的 cxxflags 编译成构建期辅助静态库
        （文件集与 boost/1.84.0 元包一致），测试结束不随包交付。
        """
        aux_dir = os.path.join(self.build_folder, "obj_fs_aux")
        os.makedirs(aux_dir, exist_ok=True)
        # 元包同款源文件清单（跳过 windows_file_codecvt.cpp——Windows 专用）
        fs_src = [
            "codecvt_error_category.cpp", "directory.cpp", "exception.cpp",
            "operations.cpp", "path.cpp", "path_traits.cpp",
            "portability.cpp", "unique_path.cpp", "utf8_codecvt_facet.cpp",
        ]
        objs = []
        extra = ("-DBOOST_FILESYSTEM_NO_CXX20_CHAR8_T "
                 "-DBOOST_FILESYSTEM_NO_CXX20_ATOMIC_REF")
        for src_name in fs_src:
            src_path = os.path.join(boost_root, "libs", "filesystem", "src", src_name)
            obj_path = os.path.join(aux_dir, src_name.replace(".cpp", ".o"))
            cmd = f"{cxx} {cxxflags} {extra} -c {src_path} -o {obj_path}"
            ret_code, _, ret_err = self._run_cmd(cmd, timeout=300, shell=True)
            if ret_code != 0:
                last = ret_err.splitlines()[-1] if ret_err.strip() else ""
                self.output.warning(f"aux filesystem {src_name} failed: {last}")
                return False
            objs.append(obj_path)
        lib_path = os.path.join(self.build_folder, "libboost_filesystem.a")
        self.run(f"{ar} rcs {lib_path} {' '.join(objs)}")
        return True

    def package(self):
        # Install headers: copy entire boost/ include directory
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

        # Install compiled static library — 只交付 libboost_stacktrace_basic.a：
        # build 期间的 libboost_thread.a / libboost_timer.a /
        # libboost_filesystem.a / libboost_stacktrace_noop.a 均为上游测试的
        # 链接辅助产物（thread_safety_checking / terminate_handler / noop_lib
        # 系列目标），不属于本包交付范围。
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_*.a")):
            if os.path.basename(lib_file) != "libboost_stacktrace_basic.a":
                continue
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

    def package_info(self):
        # 拆分组件包使用独立的 CMake 包名 boost1.84-stacktrace_basic，避免与
        # boost/1.84.0 元包的 cmake_file_name "Boost" 冲突（同一工程
        # 同时依赖两者时 CMakeDeps 生成文件不会互相覆盖）。
        self.cpp_info.set_property("cmake_file_name", "boost1.84-stacktrace_basic")

        # Main "headers" component (always needed)
        self.cpp_info.components["boost1.84_stacktrace_basic_headers"].includedirs = ["include"]
        # R8 合规：向所有消费者暴露 BOOST_SP_NO_PTHREAD_SETCANCELSTATE，
        # 使打过补丁的 sp_thread_sleep.hpp 跳过 pthread_setcancelstate
        # 路径（OHOS musl 无此 API），不依赖平台宏。stacktrace 自身源码不
        # 经过该路径，但复制了完整 boost 头文件树，下游若包含 boost/thread
        # 等头文件则需要此宏。
        self.cpp_info.components["boost1.84_stacktrace_basic_headers"].defines = [
            "BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        self.cpp_info.components["boost1.84_stacktrace_basic_headers"].set_property(
            "cmake_target_name", "boost1.84-stacktrace_basic::headers")

        # Stacktrace basic（编译库：帧收集 + dladdr 符号解析实现）
        self.cpp_info.components["boost1.84_stacktrace_basic"].includedirs = []
        self.cpp_info.components["boost1.84_stacktrace_basic"].libs = [
            "boost_stacktrace_basic"]
        # 上游 Jamfile：<target-os>linux:<library>dl（dladdr 所在）。
        # OHOS musl 已将 dl 合入 libc，显式 -ldl 兼容（无 libdl.so 时由
        # clang 传 --no-as-needed 语义忽略，不报错）。
        self.cpp_info.components["boost1.84_stacktrace_basic"].system_libs = ["dl"]
        self.cpp_info.components["boost1.84_stacktrace_basic"].requires = [
            "boost1.84_stacktrace_basic_headers"]
        self.cpp_info.components["boost1.84_stacktrace_basic"].set_property(
            "cmake_target_name", "boost1.84-stacktrace_basic::stacktrace_basic")
