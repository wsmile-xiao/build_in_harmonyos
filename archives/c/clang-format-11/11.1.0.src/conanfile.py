#!/usr/bin/env python3
"""Conan recipe — clang-format-11 11.1.0.src（LLVM clang-format 独立代码格式化工具，鸿蒙 PC aarch64）

从 llvm-project 11.1.0 官方源码构建独立的 clang-format 命令行工具（仅 AArch64 target）。
产物: bin/clang-format + bin/git-clang-format + share/clang/*（5 个集成脚本），
      对齐上游 clang/tools/clang-format/CMakeLists.txt 的全部 install() 规则
      （application 类型，R38 由软件级 commands.json 声明）。

构建策略与 clang/20.1.8 同族（鸿蒙 PC 真机原生编译）：
  1) 不设 CMAKE_SYSTEM_NAME → 不触发交叉编译 → llvm-tblgen 原生编+跑；
  2) config.guess 不认 uname -s=HarmonyOS → build() 覆盖为 stub 输出 aarch64-unknown-linux-ohos；
  3) cmake 无 Platform/HarmonyOS 模块 → 提供 include(Platform/Linux) 挂到 CMAKE_MODULE_PATH。

本地调试加速（可选）：环境变量 CLANG_FORMAT_11_WORKSPACE 指向一个持久工作区，
build() 在其中复制完整源码树并构建（源码 + build-ohos 同级），conan create 重跑时
ninja 可断点续编（本机 /tmp 只读 + 命令 300s 上限的适配手段）。CI 不设置该变量时
回退到 conan source_folder 内构建（完整自包含，行为与 clang/20.1.8 一致）。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ClangFormat11Conan(ConanFile):
    name = "clang-format-11"
    version = "11.1.0.src"
    description = "clang-format 11.1.0 —— LLVM clang-format 代码格式化命令行工具（aarch64-unknown-linux-ohos）"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://clang.llvm.org/docs/ClangFormat.html"
    url = "https://github.com/llvm/llvm-project"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="source")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _workspace(self):
        """返回 (源码容器根, 构建目录)。CLANG_FORMAT_11_WORKSPACE 未设置 → conan source_folder。"""
        _ws = os.environ.get("CLANG_FORMAT_11_WORKSPACE") or ""
        if _ws:
            if not os.path.isdir(os.path.join(_ws, "llvm")):
                os.makedirs(_ws, exist_ok=True)
                for _e in os.listdir(self.source_folder):
                    _s = os.path.join(self.source_folder, _e)
                    _d = os.path.join(_ws, _e)
                    if os.path.isdir(_s):
                        shutil.copytree(_s, _d, symlinks=True)
                    else:
                        shutil.copy2(_s, _d)
            return _ws, os.path.join(_ws, "build-ohos")
        return self.source_folder, os.path.join(self.source_folder, "build-ohos")

    def build(self):
        apply_conandata_patches(self)
        # cmake 4.x 需 policy 兼容（LLVM 11 的 cmake_minimum_required 版本过旧）
        os.environ["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        _root, _bdir = self._workspace()
        os.makedirs(_bdir, exist_ok=True)
        # 1) config.guess stub：设备 uname -s=HarmonyOS，config-ix.cmake 无条件调用它
        cg = os.path.join(_root, "llvm", "cmake", "config.guess")
        with open(cg, "w", encoding="utf-8") as _f:
            _f.write("#!/bin/sh\necho aarch64-unknown-linux-ohos\n")
        # 2) Platform/HarmonyOS.cmake（复用 Platform/Linux：置 UNIX=1）挂到 CMAKE_MODULE_PATH
        _pm = os.path.join(self.build_folder, "_cmake_modules")
        os.makedirs(os.path.join(_pm, "Platform"), exist_ok=True)
        with open(os.path.join(_pm, "Platform", "HarmonyOS.cmake"), "w", encoding="utf-8") as _f:
            _f.write("include(Platform/Linux)\n")
        # 3) 编译器/标志从 profile 的 tools.build:compiler_executables 取（R33：不裸用 shell 变量）
        _tools = self.conf.get("tools.build:compiler_executables", default={})
        _cc = _tools.get("c", "clang")
        _cxx = _tools.get("cpp", "clang++")
        _src = os.path.join(_root, "llvm")
        _defs = " ".join([
            "-G Ninja",
            '-DCMAKE_MODULE_PATH="{}"'.format(_pm),
            '-DCMAKE_C_COMPILER="{}"'.format(_cc),
            '-DCMAKE_CXX_COMPILER="{}"'.format(_cxx),
            "-DCMAKE_BUILD_TYPE=Release",
            "-DLLVM_TARGETS_TO_BUILD=AArch64",
            '-DLLVM_ENABLE_PROJECTS="clang"',   # clang-format 在 clang/tools/clang-format（LLVM 11 布局）
            "-DLLVM_ENABLE_ASSERTIONS=OFF",
            "-DLLVM_INCLUDE_EXAMPLES=OFF",
            "-DLLVM_INCLUDE_DOCS=OFF",
            "-DLLVM_ENABLE_TERMINFO=OFF",
            "-DLLVM_ENABLE_ZLIB=OFF",
            "-DLLVM_ENABLE_LIBXML2=OFF",
            "-DLLVM_ENABLE_WERROR=OFF",
            # 上游测试真实运行（R51 三步法），lit/单测基础设施需 ON
            "-DLLVM_INCLUDE_TESTS=ON",
            "-DLLVM_INCLUDE_UTILS=ON",
            "-DCMAKE_CXX_FLAGS=-stdlib=libc++",
            # 值含空格必须整体加引号（否则被 shell 拆成两个参数）
            "-DCMAKE_EXE_LINKER_FLAGS='-stdlib=libc++ -lc++abi'",
        ])
        self.run('cmake -S "{}" -B "{}" {}'.format(_src, _bdir, _defs))
        # 只构建 clang-format + 测试基础设施（FileCheck/FormatTests/count/not/llvm-config 供上游测试）
        self.run('cmake --build "{}" --target clang-format FileCheck FormatTests count not llvm-config -j 4'.format(_bdir))
        # 上游测试（R51）真实运行 + 打印统计行（供 CI L1c 日志留痕）
        self._run_upstream_tests(_bdir, _root)

    def _run_upstream_tests(self, bdir, root):
        """R51 上游测试三步法之实跑：单测 FormatTests + lit clang/test/Format，打印统计行。"""
        _unit_bin = os.path.join(bdir, "tools", "clang", "unittests", "Format", "FormatTests")
        _unit_log = os.path.join(self.build_folder, "format_unittests.log")
        self.run('"{}" > "{}" 2>&1'.format(_unit_bin, _unit_log), ignore_errors=True)
        with open(_unit_log, encoding="utf-8", errors="replace") as _f:
            _unit_out = _f.read()
        _pm = re.search(r"\[  PASSED  \] (\d+) tests?", _unit_out)
        _pn = re.search(r"\[  FAILED  \] (\d+) test", _unit_out)
        _unit_passed = int(_pm.group(1)) if _pm else 0
        _unit_failed = int(_pn.group(1)) if _pn else 0

        _fmt_src = os.path.join(root, "clang", "test", "Format")
        _lit_log = os.path.join(self.build_folder, "format_lit.log")
        self.run('cd "{}" && bin/llvm-lit -sv "{}" > "{}" 2>&1'.format(bdir, _fmt_src, _lit_log),
                 ignore_errors=True)
        with open(_lit_log, encoding="utf-8", errors="replace") as _f:
            _lit_out = _f.read()
        _lm = re.search(r"^\s*Passed: (\d+)$", _lit_out, re.MULTILINE)
        _ln = re.search(r"^\s*Unexpectedly Failed: (\d+)$", _lit_out, re.MULTILINE)
        _lit_passed = int(_lm.group(1)) if _lm else 0
        _lit_failed = int(_ln.group(1)) if _ln else 0

        self.output.info(
            "UPSTREAM TESTS: unit {}/{} passed, lit {}/{} passed — total passed {} failed {}".format(
                _unit_passed, _unit_passed + _unit_failed,
                _lit_passed, _lit_passed + _lit_failed,
                _unit_passed + _lit_passed, _unit_failed + _lit_failed))
        if _unit_failed or _lit_failed:
            raise Exception("upstream tests failed: unit failed={} lit failed={}".format(
                _unit_failed, _lit_failed))

    def package(self):
        # 收全上游 clang-format 组件的交付物（逐条对齐 clang/tools/clang-format/CMakeLists.txt
        # 的 install() 规则）：
        #   bin/clang-format        ← add_clang_tool(clang-format)
        #   bin/git-clang-format    ← install(PROGRAMS ... DESTINATION bin)（git 集成脚本）
        #   share/clang/<5 个脚本>   ← install(PROGRAMS ... DESTINATION share/clang)
        #   LICENSE                 ← clang 子项目 LICENSE.TXT
        # 上游 clang-format-fuzzer 为 EXCLUDE_FROM_ALL 且无 install 规则，不属于交付物。
        _root, _bdir = self._workspace()
        _tool_dir = os.path.join(_root, "clang", "tools", "clang-format")
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        # 主程序取构建产物；git-clang-format 是源码树内的 Python 脚本（不参与编译）
        _bin_srcs = {
            "clang-format": os.path.join(_bdir, "bin", "clang-format"),
            "git-clang-format": os.path.join(_tool_dir, "git-clang-format"),
        }
        for _name, _src in _bin_srcs.items():
            shutil.copy2(_src, os.path.join(self.package_folder, "bin", _name))
            os.chmod(os.path.join(self.package_folder, "bin", _name), 0o755)
        # share/clang/：LLVM 11 对下列 5 个文件均用 install(PROGRAMS)（含可执行位）
        _share = os.path.join(self.package_folder, "share", "clang")
        os.makedirs(_share, exist_ok=True)
        for _f in ("clang-format-diff.py", "clang-format-sublime.py", "clang-format.el",
                   "clang-format.py", "clang-format-bbedit.applescript"):
            shutil.copy2(os.path.join(_tool_dir, _f), os.path.join(_share, _f))
            os.chmod(os.path.join(_share, _f), 0o755)
        # clang 子项目 LICENSE.TXT（Apache-2.0 WITH LLVM-exception；llvm-project 根无 LICENSE 文件）
        os.makedirs(os.path.join(self.package_folder, "licenses"), exist_ok=True)
        shutil.copy2(os.path.join(_root, "clang", "LICENSE.TXT"),
                     os.path.join(self.package_folder, "licenses", "LICENSE.TXT"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["c++_shared"]
