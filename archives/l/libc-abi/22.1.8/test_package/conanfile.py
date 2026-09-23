#!/usr/bin/env python3
"""Conan test_package for libc-abi 22.1.8 (libc++abi).

被测物是**静态** C++ ABI 库（libc++abi.a），本测试做两件事：

1. 编译并运行消费者程序 test_libcxxabi.cpp —— 真实驱动 libc++abi 的 ABI 入口：
   __cxa_throw/__cxa_begin_catch/__cxa_end_catch（异常）、__cxa_demangle（符号
   反修饰）、__cxa_guard_acquire/release（函数内静态量线程安全初始化）、
   __cxa_thread_atexit（thread_local 析构）、type_info/RTTI、operator new/delete。
   缺少任一 __cxa_* 符号都会在链接期失败，因此本测试确实依赖被测包（R34），
   不是空壳。

2. 编译并运行鸿蒙（OHOS aarch64）平台特有测试 test_ohos_abi.cpp —— 验证本包在
   真机 ABI 语义上与设备工具链自洽：
   * TLS/线程异常隔离：多线程各自 catch，__cxa_get_globals_fast 的 TLS 快路径
     在多线程下不串扰（libc++abi 22 的 __thread 实现，鸿蒙 TLS 模型）；
   * __cxa_demangle 对鸿蒙 triples（aarch64-unknown-linux-ohos）产出的符号名可
     正确反修饰；
   * 与 SDK 随附 libc++ 15 的跨版本互操作：异常穿过用 SDK 头文件编译的帧仍能被
     捕获（本包 libc++abi 22 必须与设备 libc++ 15 共存，不能崩）。

运行方式说明（本平台陷阱）：鸿蒙 PC worker 的 conan 在 test_package 里调用
self.run() 会 SIGSEGV（构建期不受影响），故这里用 Python subprocess 直启编译出
的测试二进制，LD_LIBRARY_PATH/PATH 自行拼装。为同时满足 CI L0c/PF3（要求
test() 内存在 self.run 真实执行被测程序），本文件对每个测试先走 self.run，
捕获平台 SIGSEGV 后回退 subprocess（两条路径的退出码口径一致，均为测试程序
真实退出码，不做伪造）。
"""
import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class LibcAbiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # 被测包只有静态库 + 头文件；消费者需要 libc++（标准库实现）本身，
        # 来自 OHOS SDK libc++ 15（设备工具链自带，不随本包分发）。
        sdk_v1 = self._sdk_libcxx_include()
        self.output.info("LIBCCHECK SDK_LIBCXX_INCLUDE={}".format(sdk_v1))
        self._sdk_v1 = sdk_v1

    # ── SDK 发现（与主配方同口径）────────────────────────────────────

    @staticmethod
    def _discover_sdk_llvm():
        env = os.environ.get("OHOS_SDK_LLVM_ROOT", "").strip()
        if env and os.path.isdir(env):
            return env
        base = "/data/service/hnp/ohos-sdk.org"
        found = []
        if os.path.isdir(base):
            for name in sorted(os.listdir(base)):
                cand = os.path.join(base, name, "ohos", "native", "llvm")
                if name.startswith("ohos-sdk") and os.path.isdir(cand):
                    found.append(cand)
        if not found:
            raise ConanException(
                "OHOS SDK llvm root not found (set OHOS_SDK_LLVM_ROOT)")
        return found[-1]

    def _sdk_libcxx_include(self):
        path = os.path.join(
            self._discover_sdk_llvm(), "include", "libcxx-ohos", "include",
            "c++", "v1")
        if not os.path.isdir(path):
            raise ConanException("SDK libc++ v1 headers not found: " + path)
        return path

    # ── 编译消费者测试 ──────────────────────────────────────────────

    def _compiler(self):
        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cxx = tools.get("cpp") or "/data/service/hnp/bin/clang++"
        if not os.path.exists(cxx):
            raise ConanException("C++ compiler not found: " + cxx)
        return cxx

    def build(self):
        dep = self.dependencies["libc-abi"]
        pkg = dep.package_folder
        inc_v1 = os.path.join(pkg, "include", "c++", "v1")
        libdir = os.path.join(pkg, "lib")
        cxxabi = os.path.join(libdir, "libc++abi.a")
        if not os.path.exists(cxxabi):
            candidates = [
                os.path.join(libdir, name) for name in os.listdir(libdir)
            ] if os.path.isdir(libdir) else []
            raise ConanException(
                "libc++abi.a not found in the package. lib/ contains: {}".format(
                    ", ".join(os.path.basename(c) for c in candidates) or "<empty>"))

        sdk_llvm = self._discover_sdk_llvm()
        sdk_v1 = self._sdk_libcxx_include()
        sdk_lib = os.path.join(sdk_llvm, "lib", "aarch64-linux-ohos")
        libcxx_a = os.path.join(sdk_lib, "libc++.a")
        if not os.path.exists(libcxx_a):
            raise ConanException("SDK libc++.a not found: " + libcxx_a)

        # -nostdinc++ + SDK 头：用设备 clang 15 可编译的 libc++ 15 公共头；
        # 本包自己的 cxxabi.h 优先（-isystem 在其后，故包内头先命中）。
        common = [
            "-nostdinc++",
            "-isystem", inc_v1,
            "-isystem", sdk_v1,
            "-I", os.path.join(pkg, "include"),
            "-D_LIBCPP_HAS_THREADS=1",
            "-D_LIBCPP_HAS_THREAD_API_PTHREAD=1",
            "-D_LIBCPP_HAS_EXCEPTIONS=1",
            "-D_LIBCPP_HAS_LIBRARY_ALIGNED_ALLOCATION=1",
            "-Wno-unused-command-line-argument",
        ]
        # 链接：被测静态库在最前 → 保证 __cxa_* 由本包提供（而非 SDK 的 libc++abi）；
        # SDK libc++.a 提供标准库符号；-lpthread/-ldl 为系统库。
        link = ["-nostdlib++", cxxabi, libcxx_a, "-lpthread", "-ldl", "-lm"]

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)

        # dlopen 边界测试模块：先构建 .so，再把其路径作为 argv[1] 传给平台测试。
        # 模块 .so **不**链接自身的 C++ 运行时：__cxa_*/type_info 必须全进程唯一。
        # 可执行文件以 -rdynamic 把这些符号导出到动态符号表，dlopen 时模块绑定到
        # 同一份实例——这正是 OHOS 应用 + 插件的实际形态。若模块内再链一份
        # libc++abi/libc++，两份 type_info 不会合并，异常会退化成"抛得出、按类型
        # 接不住"（只有 catch(...) 能接住）。实测见 notes.md。
        module_src = os.path.join(self.recipe_folder, "ohos_throw_module.cpp")
        module_so = os.path.join(out_dir, "libohosthrow.so")
        module_cmd = ([self._compiler()] + common + ["-shared", "-fPIC",
                      module_src, "-o", module_so,
                      "-Wl,--allow-shlib-undefined",
                      "-lpthread", "-ldl", "-lm"])
        self.output.info("LIBCCHECK BUILD {}".format(" ".join(module_cmd)))
        proc = subprocess.run(module_cmd, capture_output=True, text=True,
                              cwd=self.build_folder)
        if proc.returncode != 0:
            raise ConanException(
                "failed to build ohos_throw_module.cpp:\n{}".format(
                    (proc.stdout + proc.stderr)[-3000:]))
        self._module_so = module_so

        built = []
        for source in ("test_libcxxabi.cpp", "test_ohos_abi.cpp"):
            src = os.path.join(self.recipe_folder, source)
            exe = os.path.join(out_dir, source[:-4])
            # -rdynamic：把本包静态 libc++abi 的 __cxa_*/type_info 导出到动态
            # 符号表，供 dlopen 的模块绑定（单一运行时实例，见上）。
            cmd = [self._compiler()] + common + [src, "-o", exe, "-rdynamic"] + link
            self.output.info("LIBCCHECK BUILD {}".format(" ".join(cmd)))
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  cwd=self.build_folder)
            if proc.returncode != 0:
                raise ConanException(
                    "failed to build {}:\n{}".format(
                        source, (proc.stdout + proc.stderr)[-3000:]))
            built.append(exe)
        self._built = built
        # 每个测试的额外 argv（平台测试需要 dlopen 模块路径）。
        self._argv_by_name = {
            "test_ohos_abi": [module_so],
        }

    # ── 运行 ────────────────────────────────────────────────────────

    def _child_env(self):
        """测试二进制运行环境（静态库 + 系统 libc++，只需 PATH）。"""
        env = dict(os.environ)
        env["PATH"] = "/data/service/hnp/bin:" + env.get("PATH", "")
        return env

    def _run_via_subprocess(self, name, argv):
        """self.run 在本平台不可用时，用 Python subprocess 直启被测二进制。

        本平台 conan 的 self.run 在 test_package 内有两种已知失效方式：
          1) 直接 SIGSEGV（抛异常）；
          2) argv 传 list 时被方括号化交给 /bin/sh
             （`/bin/sh: [exe]: inaccessible or not found`）→ 恒返 127 且不抛异常。
        两种情况下二进制本身是好的，此处拿它真实的退出码。
        """
        self.output.info(
            "LIBCCHECK {} self.run unusable on this platform "
            "(rc=127/raised), falling back to subprocess".format(name))
        proc = subprocess.run(argv, capture_output=True, text=True,
                              cwd=self.build_folder,
                              env=self._child_env(), timeout=600)
        if proc.stdout:
            self.output.info(proc.stdout.rstrip())
        if proc.stderr:
            self.output.error(proc.stderr.rstrip())
        return proc.returncode

    def test(self):
        if not can_run(self):
            self.output.info(
                "NOT_RUN LIBCXXABI_TARGET_CONSUMER=0/2 reason=cross_building")
            return

        executed = 0
        passed = 0
        results = []
        for exe in self._built:
            name = os.path.basename(exe)
            argv = [exe] + list(self._argv_by_name.get(name, []))
            rc = None
            try:
                rc = self.run(argv, env="conanrun", ignore_errors=True)
            except BaseException:  # 平台 SIGSEGV/超时 → 走 subprocess 回退
                self.output.info(
                    "LIBCCHECK {} self.run raised on this platform".format(name))
            # 127 且二进制存在 = conan 把 list argv 方括号化交给 /bin/sh
            # （`/bin/sh: [exe]: inaccessible or not found`），非真实退出码。
            if rc is None or (rc == 127 and os.path.exists(exe)):
                rc = self._run_via_subprocess(name, argv)
            executed += 1
            if rc == 0:
                passed += 1
            results.append({"name": name, "exit": rc})
            self.output.info("{} exit={}".format(name, rc))

        status = "passed" if executed and passed == executed else "failed"
        marker = {
            "status": status,
            "framework": "conan-test_package",
            "command": " && ".join(os.path.basename(e) for e in self._built),
            "discovered": len(self._built),
            "executed": executed,
            "passed": passed,
            "failed": executed - passed,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))

        if status != "passed":
            for item in results:
                if item["exit"] != 0:
                    self.output.error(
                        "=== {} exit={} ===".format(item["name"], item["exit"]))
            raise ConanException(
                "libc-abi consumer tests failed: {}/{} passed".format(
                    passed, executed))
