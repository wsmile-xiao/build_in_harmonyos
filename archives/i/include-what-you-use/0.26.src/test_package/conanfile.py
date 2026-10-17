#!/usr/bin/env python3
"""test_package for include-what-you-use 0.26.src — 消费者用例 C1-C3（实质执行被测二进制，R34）。"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanException


def _sdk_llvm() -> str:
    """Locate OHOS SDK LLVM dir without hardcoding a single SDK version.

    Prefer OHOS_SDK_LLVM_ROOT; otherwise glob under /data/service/hnp/ohos-sdk.org.
    """
    env = os.environ.get("OHOS_SDK_LLVM_ROOT", "").strip()
    if env:
        if os.path.isdir(env):
            return env
        raise ConanException(
            "OHOS_SDK_LLVM_ROOT={} is not a directory".format(env)
        )
    base = "/data/service/hnp/ohos-sdk.org"
    candidates = []
    if os.path.isdir(base):
        for name in sorted(os.listdir(base)):
            if not name.startswith("ohos-sdk"):
                continue
            cand = os.path.join(base, name, "ohos", "native", "llvm")
            if os.path.isdir(cand):
                candidates.append(cand)
    return candidates[-1] if candidates else ""


def _find_sysroot() -> str:
    """Locate OHOS SDK sysroot (musl C 头): .../ohos/native/{llvm, sysroot} → dirname(llvm)/sysroot."""
    llvm = _sdk_llvm()
    if llvm:
        cand = os.path.join(os.path.dirname(llvm), "sysroot")
        if os.path.isdir(cand):
            return cand
    return ""


def _find_libcxx_inc() -> str:
    """Locate SDK libc++ headers (C++ 标准库头，iwyu 分析 C++ 文件必需)."""
    llvm = _sdk_llvm()
    if llvm:
        cand = os.path.join(llvm, "include", "libcxx-ohos", "include", "c++", "v1")
        if os.path.isdir(cand):
            return cand
    return ""


class IwyuTestConan(ConanFile):
    """test_package for include-what-you-use — 消费者用例 C1-C3（实质执行被测二进制，R34）。

    C1 基础头分析：iwyu 分析漏 <vector> 的 C++ 文件，断言报告含 "should add" 与 `#include <vector>`
    C2 确定性输出与退出码（0.26 无 --json 选项的等价断言）：
       C2a 违规文件 + -Xiwyu --error → 退出码 1；C2b include 正确的文件 → 退出码 0
    C3 文件改写（0.26 无 --fix_headers 选项，官方配套 fix_includes.py 管道）：
       `iwyu 报告(2>&1) | fix_includes.py` 改写文件，断言 include 替换 + 改写后可编译
    注：iwyu 分析报告输出在 stderr（实测），断言统一 2>&1 合并。
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["include-what-you-use"].package_folder
        iwyu = os.path.join(pkg, "bin", "include-what-you-use")
        fix_includes = os.path.join(pkg, "bin", "fix_includes.py")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        clangpp = "/data/service/hnp/bin/clang++"
        libcxx_inc = _find_libcxx_inc()
        sysroot = _find_sysroot()
        # iwyu 的内置 driver 默认搜索路径在 OHOS 设备上无 C/C++ 标准库 → -isystem 注入（system
        # 头分类，与上游 CI /usr/include 语义一致；勿用 CPATH 类环境变量——被 clang 归为 user
        # include，破坏 IWYU 归属判断，实测 25 条 e2e 失败，见 notes.md 问题台账 #5）。
        isys = []
        if libcxx_inc:
            isys += ["-isystem", libcxx_inc]
        if sysroot:
            isys += ["-isystem", os.path.join(sysroot, "usr", "include", "aarch64-linux-ohos"),
                     "-isystem", os.path.join(sysroot, "usr", "include")]
        q = shlex.quote
        c1 = os.path.join(self.source_folder, "c1_bad.cc")
        c2ok = os.path.join(self.source_folder, "c2_ok.cc")
        c3src = os.path.join(self.source_folder, "c3_fix.cc")
        c3work = os.path.join(self.build_folder, "c3_run.cc")

        # —— 冒烟：--version 可执行（签名 ELF + 自包含运行时）——
        self.run(f"{q(bash)} -c {q(iwyu + ' --version')}", env="conanrun")

        # —— C1 基础头分析：报告含 should add 段 + #include <vector> 建议 ——
        cmd1 = "out=$({iwyu} {isys} 2>&1 {c1}); " \
               "echo \"$out\" | grep -F 'should add these lines' && " \
               "echo \"$out\" | grep -F '#include <vector>'".format(
                   iwyu=q(iwyu), isys=" ".join(q(a) for a in isys), c1=q(c1))
        self.run(f"{q(bash)} -c {q(cmd1)}", env="conanrun")

        # —— C2 确定性输出与退出码（输出断言与 notes.md 申报一致，全部落入 CI 复跑）——
        # C2a: 违规文件 + --error → iwyu 退出码 1 且报告含 should-add 建议
        cmd2a = "out=$({iwyu} -Xiwyu --error {isys} 2>&1 {c1}); rc=$?; " \
                "test $rc -eq 1 && echo \"$out\" | grep -F 'should add these lines'".format(
            iwyu=q(iwyu), isys=" ".join(q(a) for a in isys), c1=q(c1))
        self.run(f"{q(bash)} -c {q(cmd2a)}", env="conanrun")
        # C2b: include 正确的文件 + --error → iwyu 退出码 0 且输出含 correct-includes 声明
        cmd2b = "out=$({iwyu} -Xiwyu --error {isys} 2>&1 {c2}); rc=$?; " \
                "test $rc -eq 0 && echo \"$out\" | grep -F 'has correct #includes/fwd-decls'".format(
            iwyu=q(iwyu), isys=" ".join(q(a) for a in isys), c2=q(c2ok))
        self.run(f"{q(bash)} -c {q(cmd2b)}", env="conanrun")

        # —— C3 文件改写（官方 fix_includes.py 管道）+ 改写后编译门 ——
        # 用例文件经 consumer_b.h 间接见 Alpha（可编译），直接只用 Alpha →
        # iwyu 报告 add consumer_a.h / remove consumer_b.h；fix_includes.py 执行改写。
        # 注意：iwyu 遇硬编译错误（如符号不可见）rc=1 不产报告 → 用例必须"可编译但含多余 include"。
        cmd3 = "cp {src} {work} && " \
               "{iwyu} {isys} 2>&1 {work} | python3 {fix} {work} && " \
               "grep -F '#include \"consumer_a.h\"' {work} && " \
               "! grep -F '#include \"consumer_b.h\"' {work} && " \
               "{clangpp} -fsyntax-only {work}; rc=$?; rm -f {work}; exit $rc".format(
                   src=q(c3src), work=q(c3work), iwyu=q(iwyu),
                   isys=" ".join(q(a) for a in isys), fix=q(fix_includes),
                   clangpp=q(clangpp))
        self.run(f"{q(bash)} -c {q(cmd3)}", env="conanrun")
