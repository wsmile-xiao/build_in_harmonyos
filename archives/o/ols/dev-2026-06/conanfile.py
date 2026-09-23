#!/usr/bin/env python3
"""Conan recipe — ols dev-2026-06（Odin 语言 LSP 服务器）

ols 是纯 Odin 语言实现的 Language Server（LSP）。上游构建完全由 odin 编译器驱动
（build.sh / ci.sh），无 CMake/Make/Autotools、无 configure。

构建策略：
- 构建工具链为 odin 编译器（tool_requires）。odin 本体是 C++ + LLVM，运行期需要
  libLLVM.so.22.1，故同时以 tool_requires 引入 llvm/22.1.0（shared 聚合库）。
  odin 属 build context，conan 会把 tool_requires 的运行环境聚合进 conanbuild
  （VirtualBuildEnv 默认环境）：PATH 含 odin 的 bin/、LD_LIBRARY_PATH 含
  llvm/22.1.0 的 lib/。ODIN_ROOT 由本配方显式指定为 odin 包根
  （即 base/core/shared/vendor 所在目录）。
- 链接驱动 clang 由本配方解析为绝对路径并经 ODIN_CLANG_PATH 传入：odin 在链接
  阶段默认以裸名 `clang` 找链接驱动（src/linker.cpp），显式化可消除对构建环境
  PATH 的隐式依赖。
- 构建命令取上游 CI 形态（ci.sh）：`odin build src/ -show-timings -collection:src=src
  -out:ols -no-bounds-check -o:speed -define:VERSION=<ver>`。VERSION 显式固定为
  「dev-2026-06」（上游默认 `nightly-<date>-<sha>`，固定后 `ols version` 可断言且
  构建可复现）。
- 平台垫片（链接期，不改上游代码）：OHOS libc（SDK sysroot 与设备端）未导出线程
  取消符号 `pthread_cancel / pthread_setcancelstate / pthread_setcanceltype /
  pthread_testcancel`，而 ols 经 core:thread 创建请求线程与 checker worker，
  直接编译会报 `ld.lld: error: undefined symbol: pthread_setcancelstate`。
  本配方在 build() 内生成无害空桩并用 `-extra-linker-flags:<stub.o>` 注入链接。
- 产物 bin/ols 是 ELF 可执行文件，OHOS XPM 要求代码签名（binary-sign-tool 自签）。
- 运行期资产：上游 README 要求 `builtin/` 目录位于 ols 二进制同级（ols 用
  /proc/self/exe 推断自身目录；找不到时可用环境变量 OLS_BUILTIN_FOLDER 指定），
  故随包安装到 bin/builtin/。bin/ols 的 DT_NEEDED 仅 libc.so，无第三方动态库依赖。
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy


class OlsConan(ConanFile):
    name = "ols"
    version = "dev-2026-06"
    description = "Odin 语言语言服务器（LSP，aarch64-unknown-linux-ohos）"
    license = "MIT"
    homepage = "https://github.com/DanielGavin/ols"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # ── OHOS libc 线程取消符号空桩（平台垫片，链接期注入，不改被测代码语义）──────
    # 依据：odin dev-2026-08 适配实测结论——OHOS libc（SDK sysroot 与设备端）未导出
    # 这四个符号，core:testing → core:thread 与 core:thread 本体都会引用它们，表现为
    # 链接期 `undefined symbol` 或加载期 `Error relocating ...: symbol not found`。
    _PTHREAD_STUB_C = """\
typedef unsigned long pthread_t;
int pthread_cancel(pthread_t thread) { (void)thread; return 0; }
int pthread_setcancelstate(int state, int *oldstate) { (void)state; if (oldstate) *oldstate = 0; return 0; }
int pthread_setcanceltype(int type, int *oldtype) { (void)type; if (oldtype) *oldtype = 0; return 0; }
void pthread_testcancel(void) { }
"""

    # 链接驱动搜索位置（绝对路径优先，避免裸名依赖 PATH）
    _CLANG_CANDIDATES = ("/data/service/hnp/bin/clang",)

    # ── rule4：上游测试真跑（构建期，非致命，仅记录证据）────────────────────────
    # 上游 ci.sh「CI」分支的测试入口：
    #   cd tests && odin test ../tests -collection:src=../src -o:speed \
    #     -define:ODIN_TEST_THREADS=1
    # tests/ 下 860 项 @(test)（另 3 处同形文本位于 fixtures 字符串与 /* */ 注释内）
    # 在目标平台（本机 = aarch64 HarmonyOS PC）可完整真实执行，无网络与外部资产依赖。
    _UPSTREAM_TEST_CMD = "test ../tests -collection:src=../src -o:speed -define:ODIN_TEST_THREADS=1"

    def build_requirements(self):
        # odin 编译器（构建工具）；llvm 供 odin 运行期解析 libLLVM.so.22.1
        self.tool_requires("odin/dev-2026-08")
        self.tool_requires("llvm/22.1.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build-ohos"

    # ── 工具链辅助 ────────────────────────────────────────────────────────────
    @staticmethod
    def _q(s):
        return "'{}'".format(s.replace("'", "'\\''"))

    def _tool_chain(self):
        odin_pkg = self.dependencies.build["odin"].package_folder
        llvm_pkg = self.dependencies.build["llvm"].package_folder
        odin_bin = os.path.join(odin_pkg, "bin", "odin")
        if not os.path.exists(odin_bin):
            raise RuntimeError("odin compiler not found: {}".format(odin_bin))
        llvm_lib = os.path.join(llvm_pkg, "lib")
        if not os.path.isdir(llvm_lib):
            raise RuntimeError("llvm lib dir not found: {}".format(llvm_lib))
        return odin_pkg, odin_bin, llvm_lib

    def _clang_path(self):
        """解析链接驱动 clang 的绝对路径。

        odin 在链接阶段以 `ODIN_CLANG_PATH` 或裸名 `clang` 作为链接驱动
        （上游 src/linker.cpp），裸名依赖构建环境 PATH。这里解析为绝对路径后经
        ODIN_CLANG_PATH 显式传入，去掉对该隐式前提的依赖。
        """
        candidates = [os.environ.get("ODIN_CLANG_PATH", "")] + list(self._CLANG_CANDIDATES)
        for c in candidates:
            if c and os.path.exists(c):
                return c
        found = shutil.which("clang")
        if not found:
            raise RuntimeError("clang (odin linker driver) not found")
        return found

    def _run_env(self, odin_pkg, llvm_lib, clang):
        """构造 odin 运行环境（供 subprocess 直接调用 odin 用）。

        路径全部来自 conan 依赖图（package_folder），无硬编码制品仓路径。
        odin 无 RUNPATH，DT_NEEDED 记录 libLLVM.so.22.1，缺 llvm/22.1.0 的 lib/
        时报 `Error loading shared library` 并连锁触发符号重定位失败（rc=127）。
        """
        env = dict(os.environ)
        env["ODIN_ROOT"] = odin_pkg
        env["ODIN_CLANG_PATH"] = clang
        env["PATH"] = "/data/service/hnp/bin" + os.pathsep + env.get("PATH", "")
        prev = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = llvm_lib + (os.pathsep + prev if prev else "")
        return env

    def _build_libc_shim(self, bdir, clang):
        """生成并编译 OHOS libc 线程取消符号空桩，返回 .o 绝对路径。"""
        q = self._q
        stub_c = os.path.join(bdir, "ohos_libc_compat.c")
        stub_o = os.path.join(bdir, "ohos_libc_compat.o")
        with open(stub_c, "w") as f:
            f.write(self._PTHREAD_STUB_C)
        self.run("{} --target=aarch64-linux-ohos -c {} -o {}".format(q(clang), q(stub_c), q(stub_o)))
        return stub_o

    def _diagnostics(self, clang, stub_o):
        """打印构建环境关键项（含链路驱动可用性），便于 CI 失败时定位。"""
        q = self._q
        self.run('echo "[env] PATH=$PATH"; echo "[env] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"',
                 ignore_errors=True)
        for label, path in (("clang", clang), ("ld.lld", "/data/service/hnp/bin/ld.lld"),
                            ("stub.o", stub_o)):
            self.output.info("[env] {} exists={} path={}".format(
                label, os.path.exists(path), path))
        self.run("{} --version 2>&1 | head -n 2".format(q(clang)), ignore_errors=True)
        self.run("ls -l {} 2>&1".format(q(stub_o)), ignore_errors=True)

    def _run_captured(self, cmd, cwd, log):
        """执行命令并把 stdout+stderr 完整落盘后再回显。

        上游 odin 在链接阶段失败时可能静默返回非 0（CI #51349 实测：`lld-link`
        阶段 32ms、无任何输出、rc=255），所以这里显式重定向落盘 + tail 回显，
        确保链接器的真实报错始终出现在 conan 日志与 CI 评论里。
        """
        q = self._q
        wrapper = os.path.join(self.build_folder, "run_captured.sh")
        with open(wrapper, "w") as f:
            f.write("#!/bin/sh\n"
                    'log="{log}"\n'
                    "(\n{cmd}\n) > \"$log\" 2>&1\n"
                    "rc=$?\n"
                    'echo "[captured] rc=$rc log={log}"\n'
                    'tail -n 150 "$log"\n'
                    "exit $rc\n".format(log=log, cmd=cmd))
        os.chmod(wrapper, 0o755)
        bash = "/data/service/hnp/bin/bash"
        shell = bash if os.path.exists(bash) else "sh"
        self.run("{} {}".format(q(shell), q(wrapper)), cwd=cwd)

    def build(self):
        q = self._q
        src = self.source_folder
        odin_pkg, odin_bin, llvm_lib = self._tool_chain()
        clang = self._clang_path()
        env = self._run_env(odin_pkg, llvm_lib, clang)

        bdir = self.build_folder
        os.makedirs(bdir, exist_ok=True)
        ols = os.path.join(bdir, "ols")
        stub_o = self._build_libc_shim(bdir, clang)
        self._diagnostics(clang, stub_o)

        # 与上游 ci.sh 的构建命令等价（-show-timings / -collection:src=src /
        # -no-bounds-check / -o:speed 全部取自上游），仅 -out 改为绝对路径、
        # VERSION 固定为登记版本、并注入 libc 空桩与绝对路径的链接驱动。
        # 运行环境用 conan 默认的 conanbuild（VirtualBuildEnv 聚合 build context 的
        # tool_requires：PATH 含 odin 的 bin/，LD_LIBRARY_PATH 含 llvm/22.1.0 的 lib/），
        # ODIN_ROOT 由本配方显式指定。
        cmd = " ".join([
            "ODIN_ROOT={}".format(q(odin_pkg)),
            "ODIN_CLANG_PATH={}".format(q(clang)),
            q(odin_bin),
            "build", "src/",
            "-show-timings",
            "-collection:src=src",
            "-out:{}".format(q(ols)),
            "-no-bounds-check",
            "-o:speed",
            "-define:VERSION={}".format(self.version),
            "-extra-linker-flags:{}".format(q(stub_o)),
        ])
        self.output.info("ols build command: {}".format(cmd))
        self._run_captured(cmd, cwd=src, log=os.path.join(bdir, "ols-build.log"))
        if not os.path.exists(ols):
            raise RuntimeError("ols binary not produced ({})".format(ols))

        # 签名（OHOS XPM：被 exec 的 ELF 必须签名）
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=ols))
        self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=ols))

        # 冒烟：`ols version` 是 main() 中服务端启动之前的纯 IO 退出路径
        # （src/main.odin 判 os.args[1] == "version" 即打印并 exit 0），
        # 不需要任何 conan 运行期环境（DT_NEEDED 仅 libc.so）。
        self.run("{} version | grep -qF {}".format(q(ols), q("ols version " + self.version)),
                 cwd=bdir, env=None)

        # rule4：上游测试真跑（非致命，仅记录证据）
        self._run_upstream_tests(odin_bin, src, env, stub_o)

    # ── rule4：上游测试真跑（非致命）──────────────────────────────────────────
    def _run_upstream_tests(self, odin_bin, src, env, stub_o):
        """在源码树 tests/ 目录内运行上游测试套件（cwd 必须是 tests/，与 ci.sh 一致）。

        任何异常都在此吞掉并写日志——绝不能因其失败而使包构建失败。
        """
        try:
            workdir = os.path.join(src, "tests")
            if not os.path.isdir(workdir):
                self.output.warning("[rule4] upstream-tests skipped: tests/ not found")
                return
            cmd = "{} {} -extra-linker-flags:{}".format(
                self._q(odin_bin), self._UPSTREAM_TEST_CMD, self._q(stub_o))
            proc = subprocess.run(cmd, shell=True, cwd=workdir, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=1800)
            log = proc.stdout or ""
            with open(os.path.join(self.build_folder, "upstream-tests.log"), "w") as f:
                f.write(log)

            m = re.search(r"Finished (\d+) tests?", log)
            executed = int(m.group(1)) if m else 0
            mf = re.search(r"(\d+) tests? failed", log)
            failed = int(mf.group(1)) if mf else 0
            ok = "All tests were successful" in log
            self.output.info(
                "[rule4] upstream-tests ols executed={} passed={} failed={} all_successful={} rc={}".format(
                    executed, executed - failed, failed, ok, proc.returncode))
        except Exception as exc:  # noqa: BLE001 — 非致命
            self.output.warning("[rule4] upstream-tests skipped on error: {}".format(exc))

    def package(self):
        bdir = self.build_folder
        copy(self, "ols", src=bdir, dst=os.path.join(self.package_folder, "bin"))
        # 上游 README：builtin/ 必须位于 ols 二进制同级（ols 用 /proc/self/exe 推断目录）
        copy(self, "*", src=os.path.join(self.source_folder, "builtin"),
             dst=os.path.join(self.package_folder, "bin", "builtin"))
        copy(self, "LICENSE", src=self.source_folder, dst=self.package_folder)
        # package 复制后重签保险
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        target = os.path.join(self.package_folder, "bin", "ols")
        self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=target))
        self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=target))

    def package_info(self):
        # application 型：bin/ols + bin/builtin 运行期资产，无库
        self.cpp_info.bindirs = ["bin"]
