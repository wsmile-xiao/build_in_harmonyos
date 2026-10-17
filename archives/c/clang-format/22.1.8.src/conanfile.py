#!/usr/bin/env python3
"""Conan recipe — clang-format 22.1.8.src（LLVM clang-format 代码格式化命令行工具，鸿蒙 PC aarch64）

从 llvm-project 22.1.8 官方源码构建独立的 clang-format CLI（仅 AArch64 target）。
产物: bin/clang-format（application 类型，R38 由软件级 commands.json 声明）。

构建策略（鸿蒙 PC 真机原生编译，与 clang/22.1.8、clang-format-11/11.1.0 同族）：
  1) 不设 CMAKE_SYSTEM_NAME → 不触发交叉编译 → llvm-tblgen/clang-tblgen 原生编+跑；
  2) llvm/cmake/config.guess 不认 uname -s=HarmonyOS（GetHostTriple.cmake / config-ix.cmake
     会调用它）→ build() 覆盖为 stub 输出 aarch64-unknown-linux-ohos；
  3) cmake 无 Platform/HarmonyOS 模块 → 提供 include(Platform/Linux) 挂 CMAKE_MODULE_PATH。

LLVM 22 相对 LLVM 11 的差异（已逐项核对源码树 llvm-project-22.1.8.src）：
  - clang-format 位于 clang/tools/clang-format（LLVM 11 亦然；历史上曾在 clang-tools-extra）。
  - googletest 迁到 third-party/unittest/googletest（LLVM 11 在 llvm/utils/unittest/googletest）。
  - lit 汇总行改为带百分比：`  Passed: N (100.00%)`；失败标签是 `Failed`
    （LLVM 11 记 `Unexpectedly Failed`），旧正则无法解析 → 本配方用无尾锚正则。
  - lit.llvm.use_llvm_tool 不再回退搜 PATH（use_installed=False），clang/test/lit.cfg.py 的
    use_clang(required=True) 因此必须靠 CLANG 环境变量提供 clang，否则套件首行 fatal → 0 通过。
  - cmake_minimum_required=3.20（≥3.5），cmake 4.1.2 无需 CMAKE_POLICY_VERSION_MINIMUM。

本地调试加速（可选）：环境变量 CLANG_FORMAT_22_WORKSPACE 指向持久工作区，build() 在其中构建
（源码 + build-ohos 同级），conan create 重跑时 ninja 可断点续编（本机 /tmp 只读 + 命令 300s
上限的适配手段）。CI 未设置该变量时回退到 conan source_folder 内构建（完整自包含）。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


# LD_PRELOAD 垫片：鸿蒙 /tmp 只读，而 llvm 内置 googletest 的 CapturedStream 把临时文件
# 硬编码到 "/tmp/gtest_captured_stream.XXXXXX"（gtest-port.cc，无环境变量开关）。
# 把 mkstemp 的 "/tmp/" 前缀改写到（可写）当前工作目录，路径只变短 → 原地改写仍在
# std::string 容量内。使上游单测真实完整运行，且不改任何上游源码/测试。
_GTEST_TMP_SHIM_C = (
    "#define _GNU_SOURCE\n"
    "#include <dlfcn.h>\n"
    "#include <string.h>\n"
    "int mkstemp(char *tmpl) {\n"
    "    static int (*real)(char *) = 0;\n"
    "    if (!real) real = (int (*)(char *))dlsym(RTLD_NEXT, \"mkstemp\");\n"
    "    if (tmpl && strncmp(tmpl, \"/tmp/\", 5) == 0)\n"
    "        memmove(tmpl, tmpl + 5, strlen(tmpl + 5) + 1);\n"
    "    return real(tmpl);\n"
    "}\n"
)


class ClangFormatConan(ConanFile):
    name = "clang-format"
    version = "22.1.8.src"
    description = "clang-format 22.1.8 —— LLVM clang-format 代码格式化命令行工具（aarch64-unknown-linux-ohos）"
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
        """返回 (源码容器根, 构建目录)。CLANG_FORMAT_22_WORKSPACE 未设置 → conan source_folder。"""
        _ws = os.environ.get("CLANG_FORMAT_22_WORKSPACE") or ""
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
        _root, _bdir = self._workspace()
        os.makedirs(_bdir, exist_ok=True)
        # 1) config.guess stub：设备 uname -s=HarmonyOS，LLVM 的 config.guess 不认
        #    （config-ix.cmake 无条件调用 get_host_triple，-DLLVM_HOST_TRIPLE 挡不住）。
        _cg = os.path.join(_root, "llvm", "cmake", "config.guess")
        with open(_cg, "w", encoding="utf-8") as _f:
            _f.write("#!/bin/sh\necho aarch64-unknown-linux-ohos\n")
        # 2) Platform/HarmonyOS.cmake（复用 Platform/Linux：置 UNIX=1）挂 CMAKE_MODULE_PATH。
        #    保持 native（不设 CMAKE_SYSTEM_NAME）→ 不触发 CMAKE_CROSSCOMPILING → tblgen 原生编+跑。
        #    模块目录固定在源码根（持久工作区路径），保证重复 conan create 时 cmake 参数
        #    不变 → ninja 增量续编，避免每次全量重编 188 目标（本机 300s 命令上限适配）。
        _pm = os.path.join(_root, "_cmake_modules")
        os.makedirs(os.path.join(_pm, "Platform"), exist_ok=True)
        with open(os.path.join(_pm, "Platform", "HarmonyOS.cmake"), "w", encoding="utf-8") as _f:
            _f.write("include(Platform/Linux)\n")
        # 3) 编译器/标志从 profile 的 tools.build:compiler_executables 取（R33：不裸用 shell 变量）。
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
            '-DLLVM_ENABLE_PROJECTS="clang"',   # clang-format 在 clang/tools/clang-format
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
            "-DLLVM_PARALLEL_LINK_JOBS=2",      # 内存偏紧：限制并行链接防 OOM
            "-DCMAKE_CXX_FLAGS=-stdlib=libc++",
            # 值含空格必须整体加引号（否则被 shell 拆成两个参数）
            "-DCMAKE_EXE_LINKER_FLAGS='-stdlib=libc++ -lc++abi'",
        ])
        self.run('cmake -S "{}" -B "{}" {}'.format(_src, _bdir, _defs))
        # 只构建 clang-format + 上游测试基础设施
        # （FileCheck/count/not 是 lit use_default_substitutions 中 unresolved="fatal" 的必需工具；
        #   FormatTests 为 gtest 单测；llvm-config 供 lit 基础设施；bin/llvm-lit 由 configure 生成）
        self.run('cmake --build "{}" --target clang-format FileCheck FormatTests count not llvm-config -j 4'.format(_bdir))
        # 上游测试（R51）真实运行 + 打印统计行（供 CI L1c 日志留痕）
        self._run_upstream_tests(_bdir, _root, _cc)

    def _build_gtest_tmp_shim(self, cc):
        """编译 LD_PRELOAD 垫片（把 gtest 硬编码的 /tmp/ 前缀改写到可写 cwd）。"""
        _c = os.path.join(self.build_folder, "_gtest_tmp_shim.c")
        _so = os.path.join(self.build_folder, "_gtest_tmp_shim.so")
        with open(_c, "w", encoding="utf-8") as _f:
            _f.write(_GTEST_TMP_SHIM_C)
        self.run('"{}" -shared -fPIC -o "{}" "{}"'.format(cc, _so, _c))
        return _so

    def _run_upstream_tests(self, bdir, root, cc):
        """R51 上游测试三步法之实跑：单测 FormatTests + lit clang/test/Format，打印统计行。"""
        # lit 加载 clang/test/lit.cfg.py，其中调 use_clang(required=True)。LLVM 22 的
        # lit.llvm.use_llvm_tool 不再回退搜 PATH（use_installed=False），会因找不到 clang
        # 直接 fatal（首行即 0 通过）。用其 search_env 覆盖项 CLANG 提供工具链 clang。
        # clang/test/Format 全部用例只调用 clang-format 本身，不使用 %clang，故结果不受影响。
        os.environ["CLANG"] = cc

        # CI worker 与本地设备的系统工具/环境存在差异（PATH 无 /usr/bin、toybox vs GNU
        # coreutils、locale 不同等），可能让个别 lit 用例（如 docs_updated.test 的
        # diff --strip-trailing-cr、grep/sort 依赖）表现不一致。运行测试前显式加固环境：
        #   1) 工具链目录（GNU diff/grep/python）与构建 bin 前置到 PATH；
        #   2) LC_ALL=C 固定排序/字符行为（toybox sort 与 GNU sort 的 locale 差异）；
        #   3) TMPDIR 指向可写目录（避免依赖 worker 默认 /tmp 语义）。
        _env_bins = []
        for _p in (os.path.dirname(cc), os.path.join(bdir, "bin"),
                   "/usr/bin", "/bin", "/system/bin"):
            if _p and os.path.isdir(_p):
                _env_bins.append(_p)
        _cur_path = os.environ.get("PATH", "")
        os.environ["PATH"] = os.pathsep.join(_env_bins + ([_cur_path] if _cur_path else []))
        os.environ["LC_ALL"] = "C"
        os.environ["LANG"] = "C"
        os.environ["TMPDIR"] = self.build_folder
        os.environ["TMP"] = self.build_folder

        _unit_bin = os.path.join(bdir, "tools", "clang", "unittests", "Format", "FormatTests")
        _unit_log = os.path.join(self.build_folder, "format_unittests.log")
        _shim_so = self._build_gtest_tmp_shim(cc)
        _work_dir = os.path.join(self.build_folder, "_gtest_work")
        os.makedirs(_work_dir, exist_ok=True)
        self.run('cd "{}" && LD_PRELOAD="{}" "{}" > "{}" 2>&1'.format(
            _work_dir, _shim_so, _unit_bin, _unit_log), ignore_errors=True)
        with open(_unit_log, encoding="utf-8", errors="replace") as _f:
            _unit_out = _f.read()
        _pm = re.search(r"\[  PASSED  \] (\d+) tests?", _unit_out)
        _pn = re.search(r"\[  FAILED  \] (\d+) test", _unit_out)
        _unit_passed = int(_pm.group(1)) if _pm else 0
        _unit_failed = int(_pn.group(1)) if _pn else 0
        _unit_total = _unit_passed + _unit_failed

        _fmt_src = os.path.join(root, "clang", "test", "Format")
        _lit_log = os.path.join(self.build_folder, "format_lit.log")
        # docs_updated.test 的 dump_format_help.py 以裸名调用 clang-format
        # （subprocess.Popen(["clang-format", "--help"])，CWD 继承自 lit 用例执行目录）。
        # 实测（本机 aarch64-unknown-linux-ohos + python 3.12）确认两个平台差异：
        #   1) CI worker 的 python 走 os.posix_spawn（子进程报错在 subprocess._posix_spawn），
        #      而 OHOS libc 的 posix_spawn **不按 PATH 解析裸名、只按 cwd 解析**：
        #      PATH 含 <build>/bin 仍报 ENOENT；cwd=<build>/bin 时可解析。
        #   2) 本机 python _USE_POSIX_SPAWN=False，走 fork+execvpe（会搜 PATH），
        #      故本地一直 32/32 而 CI 稳定 1/32 失败（同一用例 docs_updated.test）。
        # 修复：在 lit 用例执行目录（cwd）放 clang-format 符号链接指向本轮构建产物；
        # 同时保留 PATH 前置，兼顾 fork+execvpe 分支。不改上游源码/测试。
        _lit_cwd = os.path.join(bdir, "tools", "clang", "test", "Format")
        os.makedirs(_lit_cwd, exist_ok=True)
        _cf_link = os.path.join(_lit_cwd, "clang-format")
        if os.path.islink(_cf_link) or os.path.exists(_cf_link):
            os.remove(_cf_link)
        os.symlink(os.path.join(bdir, "bin", "clang-format"), _cf_link)
        self.run('cd "{}" && PATH="{}/bin:$PATH" bin/llvm-lit -sv "{}" > "{}" 2>&1'.format(
            bdir, bdir, _fmt_src, _lit_log), ignore_errors=True)
        with open(_lit_log, encoding="utf-8", errors="replace") as _f:
            _lit_out = _f.read()

        def _lit_count(label):
            # LLVM 22 lit 汇总行：`  Passed           : 37 (100.00%)`（label 被 ljust 填充，
            # 行尾带百分比）→ 匹配 label 冒号前的数字，不锚尾。
            _m = re.search(r"^\s*" + re.escape(label) + r"\s*:\s*(\d+)", _lit_out, re.MULTILINE)
            return int(_m.group(1)) if _m else 0

        _lit_passed = _lit_count("Passed") + _lit_count("Expectedly Failed") + _lit_count("Passed With Retry")
        _lit_failed = sum(_lit_count(_x) for _x in
                          ("Failed", "Timed Out", "Unresolved", "Unexpectedly Passed"))
        _lit_unsupported = _lit_count("Unsupported") + _lit_count("Skipped")
        _lit_total = _lit_passed + _lit_failed

        self.output.info(
            "UPSTREAM TESTS: unit {}/{} passed, lit {}/{} passed — total passed {} failed {}".format(
                _unit_passed, _unit_total, _lit_passed, _lit_total,
                _unit_passed + _lit_passed, _unit_failed + _lit_failed))
        self.output.info(
            "UPSTREAM TESTS detail: unit_total={} unit_failed={} lit_total={} lit_failed={} "
            "lit_unsupported={}".format(_unit_total, _unit_failed, _lit_total,
                                        _lit_failed, _lit_unsupported))
        if _unit_total == 0 or _lit_total == 0:
            raise Exception(
                "upstream tests did not run: unit_total={} lit_total={} "
                "(see format_unittests.log / format_lit.log)".format(_unit_total, _lit_total))
        if _unit_failed or _lit_failed:
            # R44：失败时把失败用例行与日志尾部打进构建日志，使 CI 评论可直接定位失败用例
            if _unit_failed:
                for _line in _unit_out.splitlines():
                    if re.search(r"\[  FAILED  \]|FAILED \]", _line):
                        self.output.error("UNIT FAIL: " + _line.strip())
                self.output.error("format_unittests.log tail:\n" +
                                  "\n".join(_unit_out.splitlines()[-40:]))
            if _lit_failed:
                for _line in _lit_out.splitlines():
                    if re.search(r"^(FAIL|error:|Error|Timed Out|Unresolved|Unexpectedly Passed)",
                                 _line):
                        self.output.error("LIT FAIL: " + _line.strip())
                self.output.error("format_lit.log tail:\n" +
                                  "\n".join(_lit_out.splitlines()[-80:]))
            raise Exception("upstream tests failed: unit failed={} lit failed={}".format(
                _unit_failed, _lit_failed))

    def package(self):
        # 收全上游 clang-format 组件的交付物（对齐 clang/tools/clang-format/CMakeLists.txt 的
        # install() 规则）：bin/clang-format + bin/git-clang-format（git 集成脚本）+
        # share/clang/*（vim/sublime/emacs/BBEdit 集成脚本与 clang-format-diff.py）+ LICENSE。
        # 上游 fuzzer 目标为 EXCLUDE_FROM_ALL 且无 install 规则，不属于交付物。
        _root, _bdir = self._workspace()
        _tool_dir = os.path.join(_root, "clang", "tools", "clang-format")
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        shutil.copy2(os.path.join(_bdir, "bin", "clang-format"),
                     os.path.join(self.package_folder, "bin", "clang-format"))
        os.chmod(os.path.join(self.package_folder, "bin", "clang-format"), 0o755)
        # git-clang-format：上游 install(PROGRAMS ...) 到 bindir（Python3 脚本，git 子命令）
        shutil.copy2(os.path.join(_tool_dir, "git-clang-format"),
                     os.path.join(self.package_folder, "bin", "git-clang-format"))
        os.chmod(os.path.join(self.package_folder, "bin", "git-clang-format"), 0o755)
        # share/clang/：上游 install(... DESTINATION "${CMAKE_INSTALL_DATADIR}/clang")
        _share = os.path.join(self.package_folder, "share", "clang")
        os.makedirs(_share, exist_ok=True)
        for _f in ("clang-format-diff.py", "clang-format-sublime.py", "clang-format.el",
                   "clang-format.py", "clang-format-bbedit.applescript"):
            shutil.copy2(os.path.join(_tool_dir, _f), os.path.join(_share, _f))
        os.chmod(os.path.join(_share, "clang-format-diff.py"), 0o755)  # 上游 PROGRAMS
        # clang 子项目 LICENSE.TXT（Apache-2.0 WITH LLVM-exception；llvm-project 根另有 LICENSE.TXT）
        os.makedirs(os.path.join(self.package_folder, "licenses"), exist_ok=True)
        shutil.copy2(os.path.join(_root, "clang", "LICENSE.TXT"),
                     os.path.join(self.package_folder, "licenses", "LICENSE.TXT"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["c++_shared"]
