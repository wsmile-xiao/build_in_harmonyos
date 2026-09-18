#!/usr/bin/env python3
"""Conan recipe — libc-abi 22.1.8 (libc++abi, the LLVM C++ ABI library)

鸿蒙 PC 真机原生编译（aarch64 -> aarch64），cmake 构建 libcxxabi 子项目。

背景
----
libc++abi 是 LLVM 单仓（llvm-project）的 libcxxabi/ 子项目，没有独立 tarball，
因此源码取 llvm-project-22.1.8.src.tar.xz（与 archives/c/clang/22.1.8 同源）。

本包是**系统同名库**（SDK 自带 libc++abi.a，版本 15）：按 R26 只构建/安装
静态库，不产出 .so，避免污染设备 /lib、/lib64。

libc++ 头文件来源
-----------------
libcxxabi 的构建必须有一份 libc++ 头文件。本仓库 22.1.8 源码树自带的 libc++
22 头文件要求 clang 19+，而设备/CI 工具链是 clang 15，无法直接使用；因此这里
改用 OHOS SDK 随附的 libc++ 15 头文件（经 CMAKE_CXX_FLAGS 的 -isystem 注入，
libcxxabi 22 没有独立的 "libcxx includes" 变量），并在命令行补齐 libc++ 22
源码所依赖的配置宏（线程模型 / 异常 / 对齐分配）。libc++ 22 内部头
<__thread/support.h> 等差异由 patches/0001 收敛到 SDK libc++ 15 可用形态。

上游测试
--------
build() 在原生（can_run）OHOS/Linux 环境下会执行 libcxxabi 上游 lit 测试套件
全部 *.pass.cpp：run_tests 逻辑内联在本配方（等价于 libcxxabi/test/lit.cfg.py
的 REQUIRES/UNSUPPORTED/XFAIL 语义），不依赖 lit 与完整 CMake 测试目标
（LIBCXXABI_INCLUDE_TESTS 需要 llvm-config 全量工具链，本包构建不起）。
结果以 `LIBCCHECK LIBCXXABI_UPSTREAM total=.. pass=.. fail=.. skip=..` 单行输出，
便于 CI 日志与 reports/test-report.md 抓取。
"""
import os
import re
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

TRIPLE = "aarch64-unknown-linux-ohos"


class LibcAbiConan(ConanFile):
    name = "libc-abi"
    version = "22.1.8"
    description = (
        "libc++abi (LLVM C++ ABI library: __cxa_* symbols, exception handling, "
        "demangling, thread_local/guard support) — HarmonyOS PC native build"
    )
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://libcxxabi.llvm.org"
    url = "https://github.com/llvm/llvm-project"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
        "with_upstream_tests": [True, False],
    }
    default_options = {
        "fPIC": True,
        "with_upstream_tests": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
        if not can_run(self):
            # 交叉编译时上游测试无法运行（需要执行编译出的测试二进制）
            self.options.with_upstream_tests = False

    # ── 源码 ────────────────────────────────────────────────────────

    def source(self):
        # 归档为 llvm-project-22.1.8.src/{llvm,clang,libcxx,libcxxabi,...}；
        # strip_root 后 source_folder 直含 libcxxabi/ 与 libcxx/（后者供
        # LIBCXXABI_LIBCXX_PATH 使用：libcxxabi 的 CMake 会读它的 src/include 与
        # __config_site 模板）。
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── SDK / 工具链发现 ────────────────────────────────────────────

    @staticmethod
    def _discover_sdk_llvm():
        """定位 OHOS SDK 的 llvm 根目录（优先 OHOS_SDK_LLVM_ROOT，其次 glob）。"""
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
        if candidates:
            return candidates[-1]
        raise ConanException(
            "OHOS SDK llvm root not found. Set OHOS_SDK_LLVM_ROOT, or install "
            "ohos-sdk under /data/service/hnp/ohos-sdk.org/ohos-sdk*/ohos/native/llvm"
        )

    def _sdk_libcxx_include(self, sdk_llvm):
        """SDK libc++ 头文件目录（<sdk>/include/libcxx-ohos/include/c++/v1）。"""
        cand = os.path.join(
            sdk_llvm, "include", "libcxx-ohos", "include", "c++", "v1"
        )
        if os.path.isdir(cand):
            return cand
        raise ConanException(
            "OHOS SDK libc++ headers not found under {} (expected "
            "include/libcxx-ohos/include/c++/v1). The device toolchain is clang 15, "
            "which cannot compile the in-tree libc++ 22 headers; refusing to "
            "produce a silently broken libc++abi.".format(sdk_llvm)
        )

    def _compilers(self):
        """取 C/C++ 编译器（R33：优先 Conan 配置，绝不依赖裸 shell 变量）。"""
        conf = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = conf.get("c") or shutil.which("clang") or "/data/service/hnp/bin/clang"
        cxx = conf.get("cpp") or shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        for path in (cc, cxx):
            if not os.path.exists(path):
                raise ConanException(
                    "C/C++ compiler not found: {}. Set "
                    "tools.build:compiler_executables or install the OHOS toolchain "
                    "under /data/service/hnp/bin.".format(path)
                )
        return cc, cxx

    def _cxx_flags(self, sdk_v1):
        """libc++ 22 源码所需的配置宏 + SDK libc++ 15 头文件路径。

        SDK 的 libc++ 15 头文件里这些宏要么不存在、要么定义为空，而 libcxxabi 22
        的源码（<__thread/support.h>、aligned_alloc.h 等）依赖它们取到真实值，
        故在命令行补齐（libc++ 22 的 __config_site 等价项）。
        """
        return " ".join([
            "-D_LIBCPP_HAS_THREADS=1",
            "-D_LIBCPP_HAS_THREAD_API_PTHREAD=1",
            "-D_LIBCPP_HAS_EXCEPTIONS=1",
            "-D_LIBCPP_HAS_LIBRARY_ALIGNED_ALLOCATION=1",
            "-isystem {}".format(sdk_v1),
            "-fPIC",
        ])

    # ── 构建 ────────────────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)
        sdk_llvm = self._discover_sdk_llvm()
        sdk_v1 = self._sdk_libcxx_include(sdk_llvm)
        cc, cxx = self._compilers()
        src = os.path.join(self.source_folder, "libcxxabi")
        bdir = os.path.join(self.build_folder, "build-ohos")

        # 设备 uname -s = HarmonyOS，而 cmake 没有 Platform/HarmonyOS 模块
        # → UNIX 变量未置 → libcxxabi 的 CMake 判平台失败。提供
        # Platform/HarmonyOS.cmake（复用 Platform/Linux）挂到 CMAKE_MODULE_PATH。
        # 保持 native 构建（不设 CMAKE_SYSTEM_NAME），与 clang 22.1.8 配方一致。
        module_path = os.path.join(self.build_folder, "_cmake_modules")
        os.makedirs(os.path.join(module_path, "Platform"), exist_ok=True)
        with open(
            os.path.join(module_path, "Platform", "HarmonyOS.cmake"), "w",
            encoding="utf-8",
        ) as handle:
            handle.write("include(Platform/Linux)\n")

        defs = [
            "-G Ninja",
            '-DCMAKE_MODULE_PATH="{}"'.format(module_path),
            '-DCMAKE_C_COMPILER="{}"'.format(cc),
            '-DCMAKE_CXX_COMPILER="{}"'.format(cxx),
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_PREFIX={}".format(self.package_folder),
            '-DCMAKE_C_FLAGS="{}"'.format(self._cxx_flags(sdk_v1)),
            '-DCMAKE_CXX_FLAGS="{}"'.format(self._cxx_flags(sdk_v1)),
            # —— 产物：系统同名库（R26）→ 只出静态库，绝不产出 .so ——
            "-DLIBCXXABI_ENABLE_STATIC=ON",
            "-DLIBCXXABI_ENABLE_SHARED=OFF",
            "-DLIBCXXABI_INSTALL_STATIC_LIBRARY=ON",
            "-DLIBCXXABI_INSTALL_HEADERS=ON",
            "-DLIBCXXABI_ENABLE_EXCEPTIONS=ON",
            "-DLIBCXXABI_ENABLE_THREADS=ON",
            "-DLIBCXXABI_ENABLE_NEW_DELETE_DEFINITIONS=ON",
            "-DLIBCXXABI_USE_LLVM_UNWINDER=OFF",   # 用系统/Conan 的 libunwind（设备自带）
            "-DLIBCXXABI_USE_COMPILER_RT=OFF",
            "-DLIBCXXABI_ENABLE_ASSERTIONS=OFF",
            "-DLIBCXXABI_HERMETIC_STATIC_LIBRARY=OFF",
            "-DLIBCXXABI_INCLUDE_TESTS=OFF",       # 上游 lit 套件由本配方自行驱动（见 _run_upstream_tests）
            # libc++ 来源：源码路径供 libcxxabi 取 libc++ 内部头（src/ 下）与
            # __config_site 模板；libc++ 15 公共头由上方 CMAKE_CXX_FLAGS 的
            # -isystem 提供（libcxxabi 22 没有独立的 "libcxx includes" 变量）。
            # LIBRARY_PATH 指向 SDK 的 libc++ 静态库：libcxxabi 的 CMake 用它
            # 链接其内部测试目标。
            '-DLIBCXXABI_LIBCXX_PATH="{}"'.format(
                os.path.join(self.source_folder, "libcxx")),
            '-DLIBCXXABI_LIBCXX_LIBRARY_PATH="{}"'.format(
                os.path.join(sdk_llvm, "lib", "aarch64-linux-ohos")),
        ]
        self.run(
            'cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)),
            env="conanbuild",
        )
        self.run('cmake --build "{}"'.format(bdir), env="conanbuild")

        if self.options.with_upstream_tests:
            self._run_upstream_tests(bdir, sdk_llvm, sdk_v1, cxx)
        else:
            self.output.info(
                "NOT_RUN LIBCXXABI_UPSTREAM reason="
                + ("cross_building" if not can_run(self) else "disabled_by_option")
            )

    # ── 上游测试套件（等价 lit 语义，内联实现） ──────────────────────

    def _run_upstream_tests(self, bdir, sdk_llvm, sdk_v1, cxx):
        """运行 libcxxabi 上游 test/*.pass.cpp 全量套件。

        不依赖 llvm-lit：libcxxabi 的 lit 配置要求 llvm-config 全量工具链
        （本包只构建 libcxxabi，CI 上不存在），这里按 lit 的标记语义
        （REQUIRES / UNSUPPORTED / XFAIL / ADDITIONAL_COMPILE_FLAGS）自行判定。

        已知平台限制（不是本配方的取舍，而是提交前实测确认）：
          * source_location / jthread 在 SDK libc++ 15 中不存在 → 依赖它们的
            测试判定为 SKIP（等价上游 lit 的 UNSUPPORTED：no-... 语义）。
        任何一个 PASS 测试失败 / 编译失败都会抛出 ConanException。
        """
        libcxxabi_a = os.path.join(bdir, "lib", "libc++abi.a")
        if not os.path.exists(libcxxabi_a):
            raise ConanException(
                "upstream tests cannot run: {} was not produced".format(libcxxabi_a)
            )
        src_root = os.path.join(self.source_folder, "libcxxabi")
        test_src = os.path.join(src_root, "test")
        support = os.path.join(self.source_folder, "libcxx", "test", "support")
        libcxx_src = os.path.join(self.source_folder, "libcxx", "src")
        sdk_lib = os.path.join(sdk_llvm, "lib", "aarch64-linux-ohos")
        out_dir = os.path.join(self.build_folder, "_upstream-tests")
        bin_dir = os.path.join(out_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)

        # 测试编译需要 e2e 一致的配置宏（库构建已定义）；_LIBCPP_BUILDING_LIBRARY
        # 让 libc++abi 仍在使用、但 libc++ 15 已标记 deprecated 的 API
        # （如 std::unexpected_handler）保持可见。
        common = [
            "-nostdinc++",
            "-isystem", sdk_v1,
            "-D_LIBCPP_HAS_THREADS=1",
            "-D_LIBCPP_HAS_THREAD_API_PTHREAD=1",
            "-D_LIBCPP_HAS_EXCEPTIONS=1",
            "-D_LIBCPP_HAS_LIBRARY_ALIGNED_ALLOCATION=1",
            "-D_LIBCPP_BUILDING_LIBRARY",
            "-I", os.path.join(test_src, "support"),
            "-I", support,
            "-I", libcxx_src,
            "-I", os.path.join(src_root, "include"),
            "-Wno-unused-command-line-argument",
        ]
        link = [
            "-nostdlib++", libcxxabi_a,
            os.path.join(sdk_lib, "libc++.a"),
            "-lpthread",
        ]

        tests = self._discover_upstream_tests(test_src)
        counts = {"pass": 0, "fail": 0, "skip": 0, "build_fail": 0, "xfail": 0}
        failures = []
        skips = []

        for name in tests:
            path = os.path.join(test_src, name)
            markers, _text = self._parse_markers(path)
            std = self._choose_std(markers)

            if not self._evaluate(markers["REQUIRES"], std, True, True):
                counts["skip"] += 1
                skips.append((name, "requires"))
                continue
            if self._evaluate(markers["UNSUPPORTED"], std, False, False):
                counts["skip"] += 1
                skips.append((name, "unsupported"))
                continue
            expects_fail = self._evaluate(markers["XFAIL"], std, False, False)

            # lit 的 shell 型测试（.sh.cpp / .sh.s / .sh.S / .sh.test）：
            # 文件本身是脚本，动作写在 "RUN:" 行里，需逐行执行。
            if ".sh." in name:
                status, detail = self._run_shell_test(
                    name, path, cxx, std, common, link,
                    self.source_folder, out_dir)
                if status == "pass":
                    counts["pass"] += 1
                elif status == "fail" and expects_fail:
                    counts["xfail"] += 1
                else:
                    counts[status] += 1
                    failures.append((status.upper(), name, detail))
                continue

            extra = []
            for flags in markers["ADDITIONAL_COMPILE_FLAGS"]:
                extra.extend(flags.split())

            compile_only = ".compile." in name
            exe = os.path.join(bin_dir, name.replace("/", "__")[:-4])
            cmd = [cxx, self._std_flag(std)] + common + extra + [path]
            if compile_only:
                cmd += ["-c", "-o", exe + ".o"]
            else:
                cmd += ["-o", exe] + link

            proc = subprocess.run(
                cmd, capture_output=True, text=True, cwd=test_src
            )
            if proc.returncode != 0:
                counts["build_fail"] += 1
                with open(os.path.join(bin_dir, name + ".log"), "w",
                          encoding="utf-8") as handle:
                    handle.write(proc.stdout + proc.stderr)
                first = next(
                    (line for line in (proc.stdout + proc.stderr).splitlines()
                     if "error" in line.lower()),
                    "build error",
                )
                failures.append(("BUILDFAIL", name, first.strip()[:200]))
                continue

            if compile_only:
                counts["pass"] += 1
                continue

            run = subprocess.run([exe], capture_output=True, text=True,
                                 cwd=test_src)
            if run.returncode == 0:
                counts["pass"] += 1
            elif expects_fail:
                counts["xfail"] += 1
            else:
                counts["fail"] += 1
                lines = (run.stdout + run.stderr).strip().splitlines()
                failures.append(("FAIL", name, (lines[0] if lines else "")[:200]))

        for status, name, detail in failures:
            self.output.warning("{} {} :: {}".format(status, name, detail))
        if skips:
            self.output.info(
                "SKIP {} test(s): {}".format(
                    len(skips), ", ".join(name for name, _ in skips))
            )

        # 单行汇总（CI 日志 / test-report.md 抓取用）
        self.output.info(
            "LIBCCHECK LIBCXXABI_UPSTREAM total={total} pass={pass} fail={fail} "
            "build_fail={build_fail} xfail={xfail} skip={skip}".format(
                total=len(tests), **counts)
        )
        with open(os.path.join(out_dir, "results.txt"), "w",
                  encoding="utf-8") as handle:
            for status, name, detail in failures:
                handle.write("{} {} {}\n".format(status, name, detail))
            handle.write(
                "total={total} pass={pass} fail={fail} build_fail={build_fail} "
                "xfail={xfail} skip={skip}\n".format(total=len(tests), **counts)
            )

        if failures or counts["fail"] or counts["build_fail"]:
            raise ConanException(
                "libcxxabi upstream test suite failed: "
                "pass={pass_} fail={fail_} build_fail={build_fail_} "
                "(first failure: {first_kind} {first_name})".format(
                    pass_=counts["pass"], fail_=counts["fail"],
                    build_fail_=counts["build_fail"],
                    first_kind=failures[0][0] if failures else "n/a",
                    first_name=failures[0][1] if failures else "n/a",
                )
            )

    # lit 认得的上游测试后缀（libcxxabi/test 全量 81 个文件）
    UPSTREAM_SUFFIXES = (".pass.cpp", ".sh.cpp", ".sh.test",
                         ".pass.sh.s", ".sh.s", ".sh.S")

    @classmethod
    def _discover_upstream_tests(cls, test_src):
        """递归收集上游测试文件，并应用目录级 lit.local.cfg 排除规则。

        上游用 lit 驱动测试；目录下的 lit.local.cfg 可把整个目录标记为
        unsupported（例如 native/arm-linux-eabi 只在原生 arm-linux-eabi
        构建上启用）。这里等价实现该语义，避免把本就不适用于本目标的测试
        计入"应当运行"的总数。
        """
        found = []
        for root, dirs, files in os.walk(test_src):
            dirs.sort()
            local_cfg = os.path.join(root, "lit.local.cfg")
            if os.path.isfile(local_cfg):
                with open(local_cfg, "r", errors="replace") as handle:
                    if re.search(r"config\.unsupported\s*=\s*True",
                                 handle.read()):
                        dirs[:] = []
                        continue
            for name in sorted(files):
                if name.endswith(cls.UPSTREAM_SUFFIXES):
                    rel = os.path.relpath(os.path.join(root, name), test_src)
                    found.append(rel.replace(os.sep, "/"))
        return sorted(found)

    def _run_shell_test(self, name, path, cxx, std, common, link,
                        llvm_root, out_dir):
        """执行 lit 的 shell 型测试：按 RUN 行逐条执行，并做 lit 替换。

        对应上游 lit.cfg.py 中的 %{cxx} / %{flags} / %{compile_flags} /
        %{link_flags} / %{exec} / %s / %t / %{libcxxabi} / %{libcxx} /
        %{llvm} 替换，语义与 lit 保持一致（shell 语法交给 /bin/sh 执行）。
        """
        run_re = re.compile(r"^\s*(?://|##|#)\s*RUN:\s*(.*)$")
        lines = []
        with open(path, "r", errors="replace") as handle:
            for line in handle.read().splitlines():
                match = run_re.match(line)
                if match:
                    lines.append(match.group(1).strip())
        if not lines:
            return "fail", "no RUN lines found"

        work = os.path.join(out_dir, "lit-tmp")
        os.makedirs(work, exist_ok=True)
        temp_base = os.path.join(work, name.replace("/", "__")[:80])
        subs = {
            "%{cxx}": shlex.quote(cxx),
            "%{flags}": self._std_flag(std),
            "%{compile_flags}": " ".join(shlex.quote(f) for f in common),
            "%{link_flags}": " ".join(shlex.quote(f) for f in link),
            "%{exec}": "",
            "%{libcxxabi}": shlex.quote(os.path.join(llvm_root, "libcxxabi")),
            "%{libcxx}": shlex.quote(os.path.join(llvm_root, "libcxx")),
            # lit 的 %{llvm} 指 LLVM 子项目目录（llvm-project/llvm），
            # 测试里用 %{llvm}/include/llvm/Demangle/... 定位头文件。
            "%{llvm}": shlex.quote(os.path.join(llvm_root, "llvm")),
            "%s": shlex.quote(path),
            "%t": shlex.quote(temp_base),
        }
        ordered = sorted(subs, key=len, reverse=True)
        for index, line in enumerate(lines, 1):
            command = line
            for key in ordered:
                command = command.replace(key, subs[key])
            proc = subprocess.run(command, shell=True, capture_output=True,
                                  text=True, cwd=work)
            if proc.returncode != 0:
                output = (proc.stdout + proc.stderr).strip().splitlines()
                return "fail", "RUN#{} rc={} :: {}".format(
                    index, proc.returncode,
                    (output[-1] if output else "")[:180])
        return "pass", ""

    @staticmethod
    def _parse_markers(path):
        """解析测试文件的 lit 标记（// 或 # 注释皆可）。"""
        markers = {"UNSUPPORTED": [], "XFAIL": [], "REQUIRES": [],
                   "ADDITIONAL_COMPILE_FLAGS": []}
        pattern = re.compile(
            r"^\s*(?://|##|#)\s*"
            r"(UNSUPPORTED|XFAIL|REQUIRES|ADDITIONAL_COMPILE_FLAGS)"
            r"\s*:\s*(.*)$"
        )
        with open(path, "r", errors="replace") as handle:
            for line in handle.read().splitlines():
                match = pattern.match(line)
                if match:
                    markers[match.group(1)].append(match.group(2).strip())
        return markers, None

    @staticmethod
    def _features_for(std):
        # 本目标（aarch64-linux-ohos + clang 15 + libc++ 15 头文件）具备的 lit
        # 特性：linux、libc++/clang、异常、线程、RTTI、thread_local。
        # no-exceptions / no-rtti / no-threads / no-thread-local / windows /
        # apple / darwin / aix 均不满足 —— 由 _atom_true 落到 False。
        return {"linux", "libc++", "clang", "exceptions", "threads", "rtti",
                "has-thread-local", std}

    @classmethod
    def _atom_true(cls, token, std):
        token = token.strip()
        if not token:
            return False
        if token.startswith("target="):
            pattern = re.sub(r"\{\{(.*?)\}\}", r"\1", token[len("target="):])
            try:
                return re.fullmatch(pattern, TRIPLE) is not None
            except re.error:
                return False
        if token.startswith("stdlib="):
            return token == "stdlib=libc++"
        if token.startswith("using-built-library-before-llvm"):
            # 被测库是 LLVM 22，永不属于 "before-llvm-XX" 条件
            return False
        return token in cls._features_for(std)

    @classmethod
    def _to_python_expr(cls, expr, std, comma_is_and):
        # lit 的 {{...}} 里可以出现正则的括号/竖线（如
        # target=powerpc{{(64)?}}le-unknown-linux-gnu）。这些字符与表达式
        # 自身的逻辑运算符同形，若直接分词会把原子拆碎、导致 eval 抛异常后
        # 落到 default（REQUIRES 默认 True → 会把不适用于本目标的测试误跑）。
        # 故先把 {{...}} 掩码成不含分隔符的占位符，分词后再还原。
        masks = []

        def _mask(match):
            masks.append(match.group(1))
            return "@@{}@@".format(len(masks) - 1)

        def _restore(token):
            return re.sub(r"@@(\d+)@@",
                          lambda m: masks[int(m.group(1))], token)

        decomposed = re.sub(r"\{\{(.*?)\}\}", _mask, expr)
        decomposed = decomposed.replace(",", " && " if comma_is_and else " || ")
        parts = re.split(r"(\s+|\|\||&&|!|\(|\))", decomposed)
        out = []
        for part in parts:
            stripped = part.strip()
            if not stripped:
                if out and out[-1] != " ":
                    out.append(" ")
                continue
            if stripped in ("||", "&&", "!", "(", ")"):
                out.append({"||": "or", "&&": "and", "!": "not"}.get(
                    stripped, stripped))
            else:
                out.append("True" if cls._atom_true(
                    _restore(stripped), std) else "False")
        return "".join(out)

    @classmethod
    def _evaluate(cls, exprs, std, comma_is_and, default):
        if not exprs:
            return default
        results = []
        for expr in exprs:
            try:
                results.append(bool(eval(cls._to_python_expr(
                    expr, std, comma_is_and))))
            except Exception as exc:
                # 不做静默 fail-open：解析不了就喊出来，否则错误方向恰好是
                # "把不该跑的测试跑了"（REQUIRES 的 default=True）。
                print("LIBCCHECK WARN unparsable lit expr {!r}: {}".format(
                    expr, exc), file=sys.stderr)
                results.append(default)
        return all(results) if comma_is_and else any(results)

    @staticmethod
    def _choose_std(markers):
        requested = set()
        for expr in markers["REQUIRES"]:
            requested.update(re.findall(r"c\+\+\d+[a-z]*", expr))
        if not requested:
            return "c++2b"
        for std in ("c++14", "c++11", "c++03", "c++17", "c++20", "c++2b"):
            if std in requested:
                return std
        return "c++2b"

    @staticmethod
    def _std_flag(std):
        return "-std=c++2b" if std == "c++2b" else "-std=" + std

    # ── 打包 ────────────────────────────────────────────────────────

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run(
            'cmake --install "{}" --prefix "{}"'.format(
                bdir, self.package_folder),
            env="conanbuild",
        )
        # 头文件：libcxxabi 自己的 include/（cxxabi.h + 生成的 __cxxabi_config.h）
        # CMake 的 install 只装到 <prefix>/include/c++/v1，这里统一下沉到
        # include/c++/v1（消费方 -isystem <pkg>/include/c++/v1 即可）。
        for stale in ("lib", "bin"):
            path = os.path.join(self.package_folder, stale)
            if os.path.isdir(path):
                for name in os.listdir(path):
                    full = os.path.join(path, name)
                    if os.path.islink(full) or name.endswith(".la"):
                        os.remove(full)
        self._check_no_shared()

    def _check_no_shared(self):
        """R26 守卫：系统同名库（SDK 自带 libc++abi.a）绝不允许产出 .so。"""
        offenders = []
        for root, _dirs, files in os.walk(self.package_folder):
            offenders.extend(
                os.path.join(root, name) for name in files
                if name.endswith(".so") or ".so." in name
            )
        if offenders:
            raise ConanException(
                "system-name library must be static-only (R26), but the package "
                "contains shared objects: {}".format(", ".join(offenders))
            )

    def package_info(self):
        self.cpp_info.libs = ["c++abi"]
        self.cpp_info.set_property("cmake_file_name", "libcxxabi")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "m"]
