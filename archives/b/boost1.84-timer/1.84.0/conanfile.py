#!/usr/bin/env python3
"""Conan recipe — boost1.84-timer 1.84.0 (Boost.Timer split package).

Boost 1.84.0 组件拆分包之一：仅交付 Boost.Timer（libboost_timer.a）。
底稿：archives/b/boost/1.84.0/ 元包（filesystem/regex/program_options/iostreams）。

形态选型（见 notes.md）：
- 独立裁剪包（非 requires 元包）。原因：boost/1.84.0 元包只编译了
  filesystem/regex/program_options/iostreams 四个库，不含 timer——
  requires 元包拿不到 libboost_timer.a；且元包与组件包都声明
  cmake_file_name "Boost"，同工程共存时 CMakeDeps 生成文件互相覆盖会冲突。
- timer 源文件仅 2 个（auto_timers_construction.cpp/cpu_timer.cpp），
  依赖全部为 header-only（config/io/predef），无需 chrono 编译库
  （cpu_timer 用 POSIX times()/sysconf(_SC_CLK_TCK)，musl 均支持）。

Boost b2 build system is incompatible with OHOS (E068, see meta-package
notes.md), so we manually compile the timer sources into a static archive,
mirroring the meta-package recipe approach.
"""
import os
import glob
import signal
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostTimerConan(ConanFile):
    name = "boost1.84-timer"
    version = "1.84.0"
    description = "Boost.Timer 1.84.0 拆分组件包（libboost_timer 静态库，鸿蒙 PC 适配）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    # Boost b2 build system is incompatible with OHOS, so we manually compile
    # the timer sources into a static archive (same rationale as the
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
            "-DBOOST_TIMER_NO_LIB",
        ])

        # Timer sources (libs/timer/build/Jamfile.v2): auto_timers_construction,
        # cpu_timer. Dependencies (config/io/predef) are header-only; cpu_timer
        # reads the clock via POSIX times()/sysconf(_SC_CLK_TCK) which musl
        # supports — no chrono compiled library needed.
        timer_src = [
            "auto_timers_construction.cpp",
            "cpu_timer.cpp",
        ]
        self._compile_lib("timer", os.path.join(boost_root, "libs/timer/src"), timer_src, cxx, ar, cxxflags)

        # ⚠️ 上游测试集成（规则 5）：b2 在 OHOS 不兼容（E068），改为手动编译
        # 上游 libs/timer/test/Jamfile.v2 注册的全部 7 个测试目标（run 型 6 +
        # compile 型 1；inspect 为 explicit 工具目标不计入）并真实运行（绕过
        # b2），统计通过率写入报告文件。
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
        """编译并运行 Boost.Timer 上游测试目标（绕过 b2），统计通过率。

        清单严格对齐上游 libs/timer/test/Jamfile.v2 的 7 个注册测试目标
        （2026-09-06 从 boostorg/timer boost-1.84.0 实测）：
          1. [run]    example/auto_cpu_timer_example.cpp
          2. [run]    cpu_timer_info.cpp
          3. [run]    cpu_timer_test.cpp
          4. [run]    example/timex.cpp（Jamfile 传参 echo "Hello, world"）
          5. [compile] original_timer_test.cpp
          6. [run]    chrono_conflict_test.cpp
                      （Jamfile: run chrono_conflict_test.cpp
                       /boost/chrono//boost_chrono : : : <link>static —— 链接
                       boost_chrono 静态库）
          7. [run]    progress_display_test.cpp
        （inspect 为 explicit 工具目标，不是测试，不计入。）

        chrono_conflict_test 需要的 libboost_chrono.a 不在本包交付范围
        （timer 实现不依赖 chrono），但源码树 libs/chrono/src 就地可用：
        按 Jamfile <link>static 语义，用与本包 timer 库完全相同的
        cxxflags 把 chrono 的 3 个上游源文件编译成临时辅助静态库供链接
        （文件集与 boost1.84-chrono 组件包一致：chrono.cpp +
        process_cpu_clocks.cpp + thread_clock.cpp），测试结束不随包交付。
        """
        lib_dir = self.build_folder
        test_dir = os.path.join(boost_root, "libs", "timer", "test")
        example_dir = os.path.join(boost_root, "libs", "timer", "example")

        # 6) chrono_conflict_test 的辅助 boost_chrono 静态库（<link>static）。
        # 不定义 BOOST_CHRONO_VERSION：上游 b2 直接消费 /boost/chrono//boost_chrono，
        # chrono 库本身按上游默认（v1）编译，实测 v1/v2 均可链接通过。
        chrono_aux_lib = None
        chrono_obj_dir = os.path.join(lib_dir, "obj_chrono_aux")
        os.makedirs(chrono_obj_dir, exist_ok=True)
        chrono_objs = []
        for src_name in ["chrono.cpp", "process_cpu_clocks.cpp", "thread_clock.cpp"]:
            obj_path = os.path.join(chrono_obj_dir, src_name.replace(".cpp", ".o"))
            cmd = (f"{cxx} {cxxflags} "
                   f"-c {os.path.join(boost_root, 'libs', 'chrono', 'src', src_name)} "
                   f"-o {obj_path}")
            ret_code, _, ret_err = self._run_cmd(cmd, timeout=300, shell=True)
            if ret_code != 0:
                self.output.warning(
                    "chrono 辅助库编译失败，chrono_conflict_test 将按失败记录: "
                    + (ret_err.splitlines()[-1] if ret_err.strip() else ""))
                chrono_objs = None
                break
            chrono_objs.append(obj_path)
        if chrono_objs:
            chrono_aux_lib = os.path.join(lib_dir, "libboost_chrono.a")
            self.run(f"{ar} rcs {chrono_aux_lib} {' '.join(chrono_objs)}")

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

        # 1-4) run 型测试（编译 + 运行，exit 0 判通过）
        # (标签, 源文件绝对路径, 运行参数列表, 额外链接库列表)
        run_tests = [
            ("example/auto_cpu_timer_example.cpp",
             os.path.join(example_dir, "auto_cpu_timer_example.cpp"), [], []),
            ("cpu_timer_info.cpp",
             os.path.join(test_dir, "cpu_timer_info.cpp"), [], []),
            ("cpu_timer_test.cpp",
             os.path.join(test_dir, "cpu_timer_test.cpp"), [], []),
            ("example/timex.cpp",
             os.path.join(example_dir, "timex.cpp"),
             ["echo", "Hello, world"], []),
            ("chrono_conflict_test.cpp",
             os.path.join(test_dir, "chrono_conflict_test.cpp"),
             [], ["boost_chrono"]),
            ("progress_display_test.cpp",
             os.path.join(test_dir, "progress_display_test.cpp"), [], []),
        ]
        for label, src, run_args, extra_libs in run_tests:
            exe = os.path.join(
                lib_dir, f"test_{label.replace('.cpp', '').replace('/', '_')}")
            link_libs = "-lboost_timer" + (
                "".join(f" -l{name}" for name in extra_libs))
            if "boost_chrono" in extra_libs and not chrono_aux_lib:
                # 辅助库不可得时如实记失败并写明技术原因，不静默跳过
                record(False, f"{label} SKIPPED: libboost_chrono.a "
                              "(chrono 库不在本包交付范围，辅助编译失败)")
                continue
            cmd_compile = (f"{cxx} {cxxflags} -Wno-#warnings {src} "
                           f"-L{lib_dir} {link_libs} -o {exe}")
            ret_code, _, ret_err = self._run_cmd(cmd_compile, timeout=300, shell=True)
            if ret_code != 0:
                record(False, f"{label} COMPILE_FAIL: "
                              f"{ret_err.splitlines()[-1] if ret_err.strip() else ''}")
                continue
            run_code, run_out, run_err = self._run_cmd(
                [exe] + run_args, timeout=300, env=run_env)
            ok = run_code == 0
            detail = (run_out or run_err or "").strip().splitlines()
            record(ok, f"{label} rc={run_code}"
                       f"{f' ({detail[-1]})' if detail else ''}")

        # 5) compile 型：original_timer_test.cpp 应编译成功（rc == 0 通过）
        #    （Jamfile 为 compile 型，不运行；含 deprecated 头文件的
        #    #pragma message 提示是预期输出，非错误）
        src = os.path.join(test_dir, "original_timer_test.cpp")
        cmd = f"{cxx} {cxxflags} -Wno-#warnings -fsyntax-only {src}"
        ret_code, _, _ = self._run_cmd(cmd, timeout=120, shell=True)
        record(ret_code == 0,
               f"original_timer_test.cpp (compile expectation, rc={ret_code})")

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

        # Install compiled static libraries
        # 只交付 libboost_timer.a：build 期间的 libboost_chrono.a 是
        # chrono_conflict_test 的链接辅助产物（<link>static 测试依赖），
        # 不属于本包交付范围（timer 实现不依赖 chrono）。
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_*.a")):
            if os.path.basename(lib_file) != "libboost_timer.a":
                continue
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

    def package_info(self):
        # 拆分组件包使用独立的 CMake 包名 boost1.84-timer，避免与
        # boost/1.84.0 元包的 cmake_file_name "Boost" 冲突（同一工程
        # 同时依赖两者时 CMakeDeps 生成文件不会互相覆盖）。
        self.cpp_info.set_property("cmake_file_name", "boost1.84-timer")

        # Main "headers" component (always needed)
        self.cpp_info.components["boost1.84_timer_headers"].includedirs = ["include"]
        # R8 合规：向所有消费者暴露 BOOST_SP_NO_PTHREAD_SETCANCELSTATE，
        # 使打过补丁的 sp_thread_sleep.hpp 跳过 pthread_setcancelstate
        # 路径（OHOS musl 无此 API），不依赖平台宏。timer 自身源码不经过
        # 该路径，但复制了完整 boost 头文件树，下游若包含 boost/thread
        # 等头文件则需要此宏。
        self.cpp_info.components["boost1.84_timer_headers"].defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        self.cpp_info.components["boost1.84_timer_headers"].set_property("cmake_target_name", "boost1.84-timer::headers")

        # Timer
        self.cpp_info.components["boost1.84_timer"].includedirs = []
        self.cpp_info.components["boost1.84_timer"].libs = ["boost_timer"]
        self.cpp_info.components["boost1.84_timer"].requires = ["boost1.84_timer_headers"]
        self.cpp_info.components["boost1.84_timer"].set_property("cmake_target_name", "boost1.84-timer::timer")
