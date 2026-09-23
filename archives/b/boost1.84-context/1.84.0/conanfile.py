#!/usr/bin/env python3
"""Conan recipe — boost1.84-context 1.84.0.

Boost.Context is a foundational library providing cooperative context
switching (fcontext_t / fiber / callcc) built on hand-written assembly
for each architecture/ABI/OS combination. On OHOS aarch64 (ELF/AAPCS)
the upstream fcontext assembly sources (make/jump/ontop_arm64_aapcs_
elf_gas.S) compile cleanly with the llvm integrated assembler shipped
in the OHOS clang toolchain — no patches needed.

Following the boost/1.84.0 recipe in this repo: package() installs the
complete boost/ header tree (Boost libraries are tightly interdependent
and partial header trees break transitive includes).

Source set mirrors upstream libs/context/build/Jamfile.v2 for
ARM64/AAPCS/ELF + clang:

    lib boost_context
      : impl_sources            # fcontext (default impl): asm_sources
        stack_traits_sources    # posix/stack_traits.cpp
    ;

where asm_sources = asm/make_arm64_aapcs_elf_gas.S
                    asm/jump_arm64_aapcs_elf_gas.S
                    asm/ontop_arm64_aapcs_elf_gas.S

Upstream defines BOOST_CONTEXT_SOURCE when building the library itself
(<define>BOOST_CONTEXT_SOURCE at project requirements) — we replicate
that so the exported symbols match the b2-built library.

上游测试集成（规则 5）：上游 libs/context/test/ 共 6 个 .cpp，其中
5 个是真实测试用例（test_invoke / test_apply / test_fcontext /
test_fiber / test_callcc），全部自带 int main() 且依赖
boost/core/lightweight_test.hpp（非 boost_unit_test_framework）。
is_libstdcxx.cpp 是 Jamfile 的 build-check 辅助 obj（"is libstdc++"
探测，仅 gcc/libstdc++ segmented-stack 路径使用，非测试用例）。
b2 在 OHOS 不兼容（E068），改为手动编译：先编译归档
libboost_context.a，再逐个编译运行 5 个测试源，以退出码 0 判定
通过，统计写入 build_folder/upstream-tests-report.txt。手法与
boost1.84-container（PR #8456）一致。
"""
import glob
import os
import signal
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy


class BoostContextConan(ConanFile):
    name = "boost1.84-context"
    version = "1.84.0"
    description = "Boost 1.84.0 Context 组件（libboost_context.a + 完整 boost 头树，鸿蒙 PC 适配，fcontext 汇编实现经 llvm 集成汇编器编译）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

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
        与 boost1.84-container / boost1.84-date_time 同款做法）。"""
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

    def _asm_sources(self, boost_root):
        """按上游 Jamfile.v2 的 arch/abi/binary-format 矩阵选择 fcontext 汇编源。

        OHOS aarch64 = architecture=arm/address-model=64/abi=aapcs/
        binary-format=elf，对应 asm/{make,jump,ontop}_arm64_aapcs_elf_gas.S
        （上游 <toolset>clang 分支，llvm 集成汇编器直接编译 GAS 语法 .S）。
        其他非 aarch64/ELF 组合不属本配方目标平台，显式报错。
        """
        arch = str(self.settings.arch)
        if arch in ("armv8", "armv8.3", "arm64"):
            files = [
                "make_arm64_aapcs_elf_gas.S",
                "jump_arm64_aapcs_elf_gas.S",
                "ontop_arm64_aapcs_elf_gas.S",
            ]
            return [os.path.join(boost_root, "libs/context/src/asm", f) for f in files]
        raise ConanException(
            f"unsupported arch for boost1.84-context fcontext asm: {arch} "
            "(only aarch64/ELF is wired up)")

    def _compile_lib(self, cxx, ar, cxxflags):
        """编译上游 ARM64/AAPCS/ELF 汇编 + posix/stack_traits.cpp，
        归档为 libboost_context.a（与 Jamfile `lib boost_context` 同源集合）。

        - .S 汇编：clang 集成汇编器（-x assembler-with-cpp 同 GCC 语义；
          OHOS llvm 无独立 as，集成汇编器是唯一路径，实测三件套全部编译通过）
        - BOOST_CONTEXT_SOURCE：上游库自身编译时的必定义（Jamfile project
          requirements），保证导出符号与 b2 产物一致
        """
        boost_root = self.source_folder
        obj_dir = os.path.join(self.build_folder, "obj_context")
        os.makedirs(obj_dir, exist_ok=True)
        objects = []

        # 1) fcontext 汇编三件套（make/jump/ontop_arm64_aapcs_elf_gas.S）
        for src in self._asm_sources(boost_root):
            obj = os.path.join(obj_dir, os.path.basename(src).replace(".S", ".o"))
            ret, _, err = self._run_cmd(
                f"{cxx} {cxxflags} -x assembler-with-cpp -c {src} -o {obj}",
                timeout=600, shell=True)
            if ret != 0:
                raise ConanException(f"compile asm {src} failed rc={ret}: {err[-500:]}")
            objects.append(obj)

        # 2) posix/stack_traits.cpp（非 Windows 的 stack_traits 源）
        st_src = os.path.join(boost_root, "libs/context/src/posix/stack_traits.cpp")
        st_obj = os.path.join(obj_dir, "stack_traits.o")
        ret, _, err = self._run_cmd(
            f"{cxx} {cxxflags} -DBOOST_CONTEXT_SOURCE -c {st_src} -o {st_obj}",
            timeout=600, shell=True)
        if ret != 0:
            raise ConanException(f"compile stack_traits.cpp failed rc={ret}: {err[-500:]}")
        objects.append(st_obj)

        lib_path = os.path.join(self.build_folder, "libboost_context.a")
        ret, _, err = self._run_cmd(
            f"{ar} rcs {lib_path} {' '.join(objects)}", timeout=300, shell=True)
        if ret != 0:
            raise ConanException(f"archive libboost_context.a failed rc={ret}: {err[-500:]}")
        return lib_path

    def _run_upstream_tests(self, boost_root, cxx, base_flags):
        """编译并运行上游 libs/context/test/ 的 5 个测试用例。

        - 测试源自带 int main()，依赖 boost/core/lightweight_test.hpp
          （"No errors detected." 输出，非 boost_unit_test_framework）
        - 链接 build_folder 下刚归档的 libboost_context.a
        - 逐个串行编译运行（无并行 fork，单 worker 单测试，内存峰值可控）
        - is_libstdcxx.cpp 是 Jamfile build-check 辅助 obj（探测 libstdc++，
          仅 segmented-stack 路径使用），不属于测试用例，不纳入统计
        - 运行时注入 LD_LIBRARY_PATH（SDK libc++_shared.so，编译器自省定位）；
          OHOS musl 加载器仅在经 shell 启动时遵守 LD_LIBRARY_PATH，故通过
          bash export 显式注入（与 container/date_time 实测结论一致）
        """
        test_dir = os.path.join(boost_root, "libs/context/test")
        lib_dir = self.build_folder
        report_lines = []
        passed, failed = 0, 0

        libcxx_dir = self._find_libcxx_dir() if self.settings.os == "OHOS" else None

        test_sources = sorted(glob.glob(os.path.join(test_dir, "*.cpp")))
        # 剔除 Jamfile build-check 辅助 obj（非测试：见 docstring）
        test_sources = [s for s in test_sources
                        if os.path.basename(s) != "is_libstdcxx.cpp"]
        for src in test_sources:
            name = os.path.basename(src)
            exe = os.path.join(self.build_folder, "ut_" + name.replace(".cpp", ""))
            cmd_compile = (
                f"{cxx} {base_flags} {src} -L{lib_dir} -lboost_context -o {exe}")
            try:
                ret_code, _, ret_err = self._run_cmd(cmd_compile, timeout=900, shell=True)
                if ret_code != 0:
                    report_lines.append(
                        f"COMPILE_FAIL {name}: {ret_err.splitlines()[-1] if ret_err else ''}")
                    failed += 1
                    continue
                if libcxx_dir:
                    run_cmd = (
                        f"export LD_LIBRARY_PATH='{libcxx_dir}:"
                        f"${{LD_LIBRARY_PATH:-}}'; '{exe}'")
                    run_code, _, _ = self._run_cmd(run_cmd, timeout=600, shell=True)
                else:
                    run_code, _, _ = self._run_cmd([exe], timeout=600)
                ok = run_code == 0
                report_lines.append(f"{'PASS' if ok else 'FAIL'} {name} rc={run_code}")
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
        for line in report_lines[-6:]:
            self.output.info(f"[upstream-tests] {line}")
        if failed:
            raise ConanException(
                f"upstream context tests failed: {failed}/{passed + failed}")

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")

        boost_root = self.source_folder
        # 优化级别随 build_type（R8：不硬编码构建档位）；-g0 去调试信息削内存峰值
        if self.settings.build_type == "Debug":
            opt = "-O0 -g"
        else:
            opt = "-O2 -DNDEBUG -g0"
        base_flags = (
            f"-std=c++17 -stdlib=libc++ {opt} -fPIC -I{boost_root} "
            f"-DBOOST_ALL_NO_LIB"
        )

        # 1) 编译归档 libboost_context.a（上游 Jamfile ARM64/AAPCS/ELF 同源集合）
        self._compile_lib(cxx, ar, base_flags)

        # 2) 上游测试集成（规则 5）：手动编译运行 libs/context/test 5 个用例
        # CI 低内存 worker（CI-021，#41383）实测 5 个纤维/协程测试在 -O2 -g0 下
        # 链接期全部 linker signal 被杀（context 测试的模板纤维实例化比
        # container 更吃链接内存）——测试编译全部降档 -Os -DNDEBUG -g0
        # （代码尺寸优先档，模板实例化更省内存；与 boost1.84-container #8435
        # 低内存削峰同款手法，container 仅 5 个重测试降 -Os，本包 5 个测试
        # 全部降档）。库本体仍 -O2（产物性能不受影响）。Debug 档本就 -O0 不动。
        if self.settings.build_type == "Debug":
            test_flags = base_flags
        else:
            test_flags = base_flags.replace("-O2 -DNDEBUG -g0", "-Os -DNDEBUG -g0")
        self._run_upstream_tests(boost_root, cxx, test_flags)

    def package(self):
        # 安装完整 boost/ 头树（与 boost/1.84.0 配方一致：Boost 库间头文件
        # 传递依赖强，部分头树会破坏传递 include）
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE_1_0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 安装 libboost_context.a
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_*.a")):
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

    def package_id(self):
        pass

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")

        self.cpp_info.components["boost_headers"].includedirs = ["include"]
        self.cpp_info.components["boost_headers"].set_property("cmake_target_name", "Boost::headers")

        # Context 组件：libboost_context.a（fcontext 汇编实现 + posix stack_traits）
        self.cpp_info.components["boost_context"].includedirs = []
        self.cpp_info.components["boost_context"].libs = ["boost_context"]
        self.cpp_info.components["boost_context"].requires = ["boost_headers"]
        self.cpp_info.components["boost_context"].set_property("cmake_target_name", "Boost::context")
