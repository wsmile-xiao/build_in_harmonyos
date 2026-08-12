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
            "OHOS_SDK_LLVM_ROOT={} is set but not a directory".format(env)
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
    """Locate OHOS SDK sysroot so clang can find stdio.h/libc for full link+run.

    SDK 布局: .../ohos/native/{llvm, sysroot} → sysroot = dirname(llvm)/sysroot。
    """
    llvm = _sdk_llvm()
    if llvm:
        cand = os.path.join(os.path.dirname(llvm), "sysroot")
        if os.path.isdir(cand):
            return cand
    return ""


def _find_libcxx_inc() -> str:
    """Locate SDK libc++ headers (needed by our clang++ to find <iostream> etc)."""
    llvm = _sdk_llvm()
    if llvm:
        cand = os.path.join(llvm, "include", "libcxx-ohos", "include", "c++", "v1")
        if os.path.isdir(cand):
            return cand
    return ""


class ClangTestConan(ConanFile):
    """test_package for clang toolchain — compiles & runs real C/C++ programs with clang."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["clang"].package_folder
        clang = os.path.join(pkg, "bin", "clang")
        clangpp = os.path.join(pkg, "bin", "clang++")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        sysroot = _find_sysroot()
        libcxx_inc = _find_libcxx_inc()
        sdk_llvm = _sdk_llvm()
        # C/C++ 共同基础 flags：sysroot（找头文件）+ lld 链接器 + SDK lib 目录
        # （libunwind.a / libc++ 等运行时，驱动默认按 OHOS 三元组链接这些）。
        base = []
        if sysroot:
            base += [f"--sysroot={sysroot}", "-fuse-ld=lld"]
        if sdk_llvm:
            base += [f"-L{sdk_llvm}/lib/aarch64-linux-ohos"]
        # C++ 额外：libc++ 头 + libc++/libc++abi/libunwind
        cxx_args = list(base)
        if libcxx_inc:
            cxx_args += ["-isystem", libcxx_inc]
        if sdk_llvm:
            cxx_args += ["-lc++", "-lc++abi", "-lunwind"]
        q = shlex.quote
        # 1) --version 可执行（L2 smoke 等价）
        self.run(f"{q(bash)} -c {q(clang + ' --version')}", env="conanrun")
        # 2) R34 反空壳：用 clang 真实编译链接并运行 C 程序，验证工具链可用
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_clang_probe")
        c_cmd = " ".join([q(clang), q(src), "-o", q(out)] + [q(a) for a in base] + ["&&", q(out)])
        self.run(f"{q(bash)} -c {q(c_cmd)}", env="conanrun")
        # 3) clang++（C++ 前端）同样编译链接并运行 C++ 源
        srcpp = os.path.join(self.source_folder, "test.cpp")
        outpp = os.path.join(self.build_folder, "test_clangpp_probe")
        cxx_cmd = " ".join(
            [q(clangpp), q(srcpp), "-o", q(outpp)] + [q(a) for a in cxx_args] + ["&&", q(outpp)]
        )
        self.run(f"{q(bash)} -c {q(cxx_cmd)}", env="conanrun")
