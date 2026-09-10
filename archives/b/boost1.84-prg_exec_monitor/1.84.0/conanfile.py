#!/usr/bin/env python3
"""Conan recipe — boost1.84-prg_exec_monitor 1.84.0 (Boost.ProgramExecutionMonitor component package).

Boost.ProgramExecutionMonitor（boost_prg_exec_monitor 库）为简单测试程序提供
执行监控：捕获 cpp_main 返回非零 / 未捕获 C 异常 / 系统信号（除零、段错误等）/
assert 失败，统一转译为结构化错误报告与非零退出码。它是 Boost.Test 家族中
最轻量的入口（不含 unit_test_framework 的测试树/日志框架）。

上游构成（libs/test/build/Jamfile.v2 PRG_EXEC_MON_SOURCES）：
  execution_monitor.cpp + debug.cpp + cpp_main.cpp
  → libboost_prg_exec_monitor.a（本包手动 clang++ 编译归档，与上游同源集合）

组件拆分包定位（与 boost1.84-container/date_time 同系列手法）：
- b2 构建系统在 OHOS 不兼容（E068），绕过 b2 手动 clang++ 编译；
- package() 安装完整 boost/ 头树（Boost 库间头文件传递依赖强）；
- OHOS musl 无 pthread_setcancelstate：复用元包已验证的 0001 补丁
  （BOOST_SP_NO_PTHREAD_SETCANCELSTATE 特性检测宏守卫，R8 合规）。

上游测试集成（规则 5）：上游 libs/test/test/prg_exec_monitor-ts/ 共 4 个
.cpp 测试源（实测与 boost_1_84_0 tarball 一致），全部为 run-fail 型
（上游 Jamfile 注册为 [ run-fail ... ]——测试程序故意触发错误条件，
以"非零退出码"判定通过：验证 PEM 把 cpp_main 错误正确转译为非零 rc）。
b2 在 OHOS 不可用，本配方手动编译运行全部 4 个测试：
- 3 个静态链接 libboost_prg_exec_monitor（与上游
  boost_prg_exec_monitor/<link>static 一致）；
- uncatched-exception-test 用 included 模式
  （boost/test/included/prg_exec_monitor.hpp，与上游 Jamfile [ included ] 一致）。
run-fail 判定：运行 rc != 0 → PASS。
"""
import glob
import os
import signal
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class Boost184PrgExecMonitorConan(ConanFile):
    name = "boost1.84-prg_exec_monitor"
    version = "1.84.0"
    description = "Boost 1.84.0 ProgramExecutionMonitor 组件（libboost_prg_exec_monitor.a + 完整 boost 头树，测试执行监控，鸿蒙 PC 适配）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/doc/libs/1_84_0/libs/test/doc/html/boost_test/prg_exec_monitor.html"
    url = ""
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    # CI 低内存 worker 链接峰值削峰（#8435 container 同款实测配方）：
    # build#41251 @CI-019 上 4 个测试全部 linker signal 被杀（本地 16G
    # 开发机同 commit 4/4 全绿——资源病非配方错）。本包测试全部经 boost
    # 头树实例化，统一以 -Os -DNDEBUG -g0 编译链接（-Os 为 -O2 的代码
    # 尺寸优先档，模板实例化更省内存，测试语义不变——run-fail 断言逻辑
    # 不受优化级别影响）。
    _HEAVY_TESTS = frozenset({
        "result-code-test.cpp",
        "system-exception-test.cpp",
        "uncatched-exception-test.cpp",
        "user-fatal-exception-test.cpp",
    })

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # 命令执行助手（超时杀进程组 + stdin EOF 保护，防孤儿进程拖死 CI）
    # ------------------------------------------------------------------
    def _run_cmd(self, cmd, timeout, shell=False):
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

    def _find_libcxx_dir(self):
        """通过编译器自省定位 SDK libc++_shared.so 目录（无硬编码 SDK 版本路径，
        与 boost1.84-date_time / boost1.84-container 同款做法）。"""
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
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

    def _compile_lib(self, cxx, ar, cxxflags):
        """编译上游 PRG_EXEC_MON_SOURCES 同源集合归档 libboost_prg_exec_monitor.a。

        上游 libs/test/build/Jamfile.v2:
        PRG_EXEC_MON_SOURCES = execution_monitor debug cpp_main
        （src/*.cpp 均为 BOOST_TEST_SOURCE 转发翻译单元）
        """
        boost_root = self.source_folder
        src_dir = os.path.join(boost_root, "libs/test/src")
        obj_dir = os.path.join(self.build_folder, "obj_prg_exec_monitor")
        os.makedirs(obj_dir, exist_ok=True)
        objects = []
        for src_name in ("execution_monitor.cpp", "debug.cpp", "cpp_main.cpp"):
            src = os.path.join(src_dir, src_name)
            obj = os.path.join(obj_dir, src_name.replace(".cpp", ".o"))
            ret, _, err = self._run_cmd(
                f"{cxx} {cxxflags} -c {src} -o {obj}", timeout=600, shell=True)
            if ret != 0:
                raise ConanException(
                    f"compile {src_name} failed rc={ret}: {err[-500:]}")
            objects.append(obj)

        lib_path = os.path.join(self.build_folder, "libboost_prg_exec_monitor.a")
        ret, _, err = self._run_cmd(
            f"{ar} rcs {lib_path} {' '.join(objects)}", timeout=300, shell=True)
        if ret != 0:
            raise ConanException(
                f"archive libboost_prg_exec_monitor.a failed rc={ret}: {err[-500:]}")
        return lib_path

    def _run_upstream_tests(self, boost_root, cxx, base_flags):
        """编译并运行上游 libs/test/test/prg_exec_monitor-ts/ 全部 4 个测试源。

        上游注册（libs/test/test/Jamfile.v2 L220-225）全部为 run-fail：
          [ run-fail : prg_exec_monitor-ts : result-code-test : boost_prg_exec_monitor/<link>static ]
          [ run-fail : prg_exec_monitor-ts : system-exception-test : boost_prg_exec_monitor/<link>static ]
          [ run-fail : prg_exec_monitor-ts : uncatched-exception-test : included ]
          [ run-fail : prg_exec_monitor-ts : user-fatal-exception-test : boost_prg_exec_monitor/<link>static ]

        run-fail 语义：测试程序故意触发错误（返回非零/抛异常/除零/assert），
        PEM 捕获后以非零退出码报告 → 退出码非零 = 测试通过。

        运行时注入 LD_LIBRARY_PATH（SDK libc++_shared.so，编译器自省定位）；
        OHOS musl 加载器仅在经 shell 启动时遵守 LD_LIBRARY_PATH，故通过
        bash export 显式注入（与 date_time/container 实测结论一致）。
        """
        test_dir = os.path.join(boost_root, "libs/test/test/prg_exec_monitor-ts")
        lib_dir = self.build_folder
        report_lines = []
        passed, failed = 0, 0

        libcxx_dir = self._find_libcxx_dir() if self.settings.os == "OHOS" else None

        # (测试文件, 链接模式)  — included 模式不链接库（头文件自带实现）
        test_cases = [
            ("result-code-test.cpp", "static"),
            ("system-exception-test.cpp", "static"),
            ("uncatched-exception-test.cpp", "included"),
            ("user-fatal-exception-test.cpp", "static"),
        ]

        for name, link_mode in test_cases:
            src = os.path.join(test_dir, name)
            if not os.path.isfile(src):
                report_lines.append(f"MISSING {name}")
                failed += 1
                continue
            # 编译档位：CI 低内存 worker 削峰（#8435 同款）——全部测试以
            # -Os -g0 编译链接（-O2 换 -Os，模板实例化省内存；本地与 CI
            # 双环境实测 run-fail 判定不受影响）
            if name in self._HEAVY_TESTS:
                flags = base_flags.replace("-O2 -DNDEBUG -g0", "-Os -DNDEBUG -g0")
            else:
                flags = base_flags
            exe = os.path.join(self.build_folder, "ut_" + name.replace(".cpp", ""))
            if link_mode == "static":
                # 上游 [ boost_prg_exec_monitor/<link>static ]：链接静态库
                cmd_compile = (
                    f"{cxx} {flags} {src} -L{lib_dir} "
                    f"-lboost_prg_exec_monitor -o {exe}")
            else:
                # 上游 [ included ]：单头模式（boost/test/included/
                # prg_exec_monitor.hpp 自带实现，不链接库）
                cmd_compile = f"{cxx} {flags} {src} -o {exe}"
            try:
                ret_code, _, ret_err = self._run_cmd(cmd_compile, timeout=900, shell=True)
                if ret_code != 0:
                    report_lines.append(
                        f"COMPILE_FAIL {name}: "
                        f"{ret_err.splitlines()[-1] if ret_err else ''}")
                    failed += 1
                    continue
                if libcxx_dir:
                    run_cmd = (
                        f"export LD_LIBRARY_PATH='{libcxx_dir}:"
                        f"${{LD_LIBRARY_PATH:-}}'; '{exe}'")
                    run_code, _, _ = self._run_cmd(run_cmd, timeout=600, shell=True)
                else:
                    run_code, _, _ = self._run_cmd([exe], timeout=600)
                # run-fail 判定：非零退出码 = PEM 正确转译错误 = 测试通过
                ok = run_code != 0
                report_lines.append(
                    f"{'PASS' if ok else 'FAIL'} {name} "
                    f"(run-fail: rc={run_code} 非零即通过, mode={link_mode})")
                if ok:
                    passed += 1
                else:
                    failed += 1
            except Exception as exc:  # noqa: BLE001 — 单个测试异常不中断整体
                report_lines.append(f"ERROR {name}: {exc}")
                failed += 1

        report_lines.append(f"TOTAL {passed + failed}: {passed} passed / {failed} failed")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(f"上游测试报告: {report_path} ({passed}/{passed + failed} 通过)")
        for line in report_lines:
            self.output.info(f"[upstream-tests] {line}")
        if failed:
            raise ConanException(
                f"upstream prg_exec_monitor tests failed: {failed}/{passed + failed}")

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")

        boost_root = self.source_folder
        # 优化级别随 build_type（R8：不硬编码构建档位）
        if self.settings.build_type == "Debug":
            opt = "-O0 -g"
        else:
            # -g0 显式去除调试信息：CI worker 链接时内存峰值叠加被
            # signal 杀（build#41251 @CI-019 实测，本地同 commit 全绿）
            # ——砍 linker 内存最大头（#8435 同款实测结论）
            opt = "-O2 -DNDEBUG -g0"
        base_flags = (
            f"-std=c++17 -stdlib=libc++ {opt} -fPIC -I{boost_root} "
            f"-DBOOST_ALL_NO_LIB -DBOOST_TEST_NO_LIB "
            # R8：特性检测宏守卫（0001 补丁消费），非平台宏
            f"-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE"
        )

        # 1) 编译归档 libboost_prg_exec_monitor.a（上游 Jamfile 同源集合）
        self._compile_lib(cxx, ar, base_flags)

        # 2) 上游测试集成（规则 5）：手动编译运行 prg_exec_monitor-ts 全部 4 测试
        self._run_upstream_tests(boost_root, cxx, base_flags)

    def package(self):
        # 安装完整 boost/ 头树（与 boost/1.84.0 元包及同系列组件包一致：
        # Boost 库间头文件传递依赖强，部分头树会破坏传递 include）
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE_1_0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_*.a")):
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

    def package_id(self):
        pass

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")

        self.cpp_info.components["boost_headers"].includedirs = ["include"]
        self.cpp_info.components["boost_headers"].set_property("cmake_target_name", "Boost::headers")
        # R8 合规：向所有消费者传播特性检测宏（0001 补丁消费，
        # 消费者单独引用本包时跳过 pthread_setcancelstate 路径）
        self.cpp_info.components["boost_headers"].defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]

        # ProgramExecutionMonitor 组件：libboost_prg_exec_monitor.a
        # （execution_monitor + debug + cpp_main，上游 Jamfile 同源集合）
        self.cpp_info.components["boost_prg_exec_monitor"].includedirs = []
        self.cpp_info.components["boost_prg_exec_monitor"].libs = ["boost_prg_exec_monitor"]
        self.cpp_info.components["boost_prg_exec_monitor"].requires = ["boost_headers"]
        self.cpp_info.components["boost_prg_exec_monitor"].set_property("cmake_target_name", "Boost::prg_exec_monitor")
