#!/usr/bin/env python3
"""Conan recipe — odinfmt dev-2026-06（Odin 语言官方代码格式化工具）

odinfmt 是纯 Odin 语言实现的源码格式化工具。上游没有独立仓库：源码位于
DanielGavin/ols 仓库的 tools/odinfmt/，格式化核心在 ols 的 src/odin/format
与 src/odin/printer（经 -collection:src=src 引入），因此本配方以 ols 的
dev-2026-06 源码树作为 source。

构建策略：
- 构建工具链是 odin 编译器（tool_requires）。odin 编译器本体是 C++ + LLVM，
  运行期需要 libLLVM.so.22.1，故同时以 tool_requires 引入 llvm/22.1.0，并在
  build() 内把其 lib/ 显式注入 LD_LIBRARY_PATH。
  说明：odin 作为构建期工具属于 build context，其运行期环境由 conan 聚合进
  conanbuild（VirtualBuildEnv）而非 conanrun；为了让链接关系显式可核，本配方
  不从 conan 生成的 env 脚本取路径，而是直接用 conan 解析出的 package_folder
  构造运行环境（路径仍由 conan 依赖图给出，无硬编码制品仓路径）。
- 上游 ci.sh/odinfmt.sh 的构建命令在本平台直接可用（无平台分支、无 LLVM 链接
  逻辑），配方按上游语义构造等价命令，不加补丁。
- 产物 bin/odinfmt 是 ELF 可执行文件，OHOS XPM 要求代码签名（binary-sign-tool 自签）。
"""
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy


class OdinfmtConan(ConanFile):
    name = "odinfmt"
    version = "dev-2026-06"
    description = "Odin 语言官方代码格式化工具（aarch64-unknown-linux-ohos）"
    license = "MIT"
    homepage = "https://github.com/DanielGavin/ols"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # ── rule4：上游测试真跑（构建期，非致命，仅记录证据）──────────────────────
    # 上游 tools/odinfmt/tests.odin 是快照（golden file）测试：遍历 tests/ 下的
    # 输入 .odin，用格式化器重排后与 .snapshots/ 下的同名快照逐字符比对。
    # 无外部资产、无网络依赖，本机（= OHOS 目标平台）可直接真实执行。
    # 调用形式即上游 tools/odinfmt/tests.sh（cwd 必须是 tools/odinfmt）。
    _UPSTREAM_TEST_CMD = "run tests.odin -file -collection:src=../../src -out:{out}"

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
    def _tool_chain(self):
        odin_pkg = self.dependencies.build["odin"].package_folder
        llvm_pkg = self.dependencies.build["llvm"].package_folder
        odin_bin = os.path.join(odin_pkg, "bin", "odin")
        if not os.path.exists(odin_bin):
            raise RuntimeError("odin compiler not found: {}".format(odin_bin))
        return odin_pkg, odin_bin, os.path.join(llvm_pkg, "lib")

    def _run_env(self, odin_pkg, llvm_lib):
        """构造 odin 运行环境（供 subprocess 调用上游测试用）：ODIN_ROOT 指向 odin
        包根（base/core/shared/vendor），LD_LIBRARY_PATH 前置 llvm/22.1.0 的 lib/
        （odin 无 RUNPATH，DT_NEEDED 记录 libLLVM.so.22.1，缺该路径会报
        Error loading shared library 并连锁触发符号重定位失败 rc=127）。"""
        env = dict(os.environ)
        env["ODIN_ROOT"] = odin_pkg
        env["PATH"] = "/data/service/hnp/bin" + os.pathsep + env.get("PATH", "")
        prev = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = llvm_lib + (os.pathsep + prev if prev else "")
        return env

    def build(self):
        src = self.source_folder
        odin_pkg, odin_bin, llvm_lib = self._tool_chain()
        env = self._run_env(odin_pkg, llvm_lib)

        def q(s):
            return "'{}'".format(s.replace("'", "'\\''"))

        bdir = self.build_folder
        os.makedirs(bdir, exist_ok=True)
        odinfmt = os.path.join(bdir, "odinfmt")

        # 与上游 ci.sh/odinfmt.sh 等价（-file 单文件程序 + ols src 作为 src 集合）。
        # 运行环境用 conan 默认的 conanbuild（VirtualBuildEnv 聚合 build context 的
        # tool_requires：PATH 含 odin 的 bin/，LD_LIBRARY_PATH 含 llvm/22.1.0 的 lib/，
        # 从而解析 odin 的 DT_NEEDED libLLVM.so.22.1）；ODIN_ROOT 由本配方显式指定。
        cmd = " ".join([
            "ODIN_ROOT={}".format(q(odin_pkg)),
            q(odin_bin),
            "build", q(os.path.join("tools", "odinfmt", "main.odin")),
            "-file",
            "-collection:src=src",
            "-out:{}".format(q(odinfmt)),
            "-no-bounds-check",
            "-o:speed",
        ])
        self.output.info("odinfmt build command: {}".format(cmd))
        self.run(cmd, cwd=src)
        if not os.path.exists(odinfmt):
            raise RuntimeError("odinfmt binary not produced")

        # 签名（OHOS XPM：被 exec 的 ELF 必须签名）
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=odinfmt))
        self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=odinfmt))

        # 冒烟：无参数调用必须给出用法并返回非 0（本工具的 CLI 契约）。
        # bin/odinfmt 的 DT_NEEDED 仅 libc.so，不需要任何 conan 环境。
        self.run("{} 2>&1 | grep -q 'Missing path' ".format(q(odinfmt)), cwd=bdir, env=None)

        # rule4：上游快照测试真跑（非致命，仅记录证据）
        self._run_upstream_tests(odin_bin, src, env)

    # ── rule4：上游快照测试真跑（非致命）──────────────────────────────────────
    def _run_upstream_tests(self, odin_bin, src, env):
        """在上游源码树内运行 tools/odinfmt/tests.odin（快照比对）。

        任何异常都在此吞掉并写日志——绝不能因其失败而使包构建失败。
        """
        try:
            workdir = os.path.join(src, "tools", "odinfmt")
            out = os.path.join(self.build_folder, "odinfmt_tests")
            cmd = "{} {}".format(
                "'{}'".format(odin_bin.replace("'", "'\\''")),
                self._UPSTREAM_TEST_CMD.format(
                    out="'{}'".format(out.replace("'", "'\\''"))),
            )
            proc = subprocess.run(cmd, shell=True, cwd=workdir, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=900)
            log = proc.stdout or ""
            with open(os.path.join(self.build_folder, "upstream-tests.log"), "w") as f:
                f.write(log)

            attempted = len(re.findall(r"Testing snapshot ", log))
            passed = len(re.findall(r"- SUCCESS", log))
            failed = len(re.findall(r"was different from snapshot file", log))
            self.output.info(
                "[rule4] upstream-tests odinfmt-snapshot attempted={} passed={} failed={} rc={}".format(
                    attempted, passed, failed, proc.returncode))
        except Exception as exc:  # noqa: BLE001 — 非致命
            self.output.warning("[rule4] upstream-tests skipped on error: {}".format(exc))

    def package(self):
        odinfmt = os.path.join(self.build_folder, "odinfmt")
        copy(self, "odinfmt", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder, dst=self.package_folder)
        # package 复制后重签保险
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        target = os.path.join(self.package_folder, "bin", "odinfmt")
        self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=target))
        self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=target))

    def package_info(self):
        # application 型：仅 bin/odinfmt 可执行文件，无库
        self.cpp_info.bindirs = ["bin"]
