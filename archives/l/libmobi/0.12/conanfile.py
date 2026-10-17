#!/usr/bin/env python3
"""Conan recipe — libmobi 0.12 (autotools).

libmobi is a C library for parsing and writing MOBI/PRC/AZW/AZW3 e-book
documents. Configured with internal miniz + internal xmlwriter
(--with-zlib=no --with-libxml2=no) so the package has zero Conan/system
dependencies on the device — zlib and libxml2 dev headers are not
installed there and this combination is covered by upstream CI.

Tools mobitool/mobimeta are installed too (package ships bin/), hence
code signing of executables in package().
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import get, export_conandata_patches, patch
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Host Autotools closure needed to bootstrap the GitHub tag archive (it ships
# configure.ac only): autoreconf drives aclocal/automake, and libtoolize is
# required because upstream configure.ac inits libtool (LT_INIT /
# AC_PROG_LIBTOOL). aclocal/automake/libtoolize are provided deterministically
# by tool_requires(automake/1.18 + libtool/2.5.4) via VirtualBuildEnv; the
# realpath fallback below only covers hosts where those bins are also
# installed next to autoreconf.
_AUTOTOOLS_TOOLS = ("autoreconf", "aclocal", "automake", "libtoolize")
# Bounded upward search: how many parent levels above the autoreconf entry
# point (and its realpath) are probed for bin/libexec tool directories.
_AUTOTOOLS_SEARCH_DEPTH = 4


class LibmobiConan(ConanFile):
    name = "libmobi"
    version = "0.12"
    description = "C library for parsing and writing MOBI/PRC/AZW/AZW3 e-book documents"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/bfabiszewski/libmobi"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # internal-libs build: bundled miniz + xmlwriter, no external deps
        pass

    def build_requirements(self):
        # E443/PR#8033: 确定性提供 autotools 闭包。GitHub tag 归档只带
        # configure.ac，autoreconf 需驱动 aclocal/automake，configure.ac 的
        # LT_INIT/AC_PROG_LIBTOOL 还需 libtoolize。仓库先例（abiword-plugin-*
        # 全系）：automake/1.18 提供 aclocal+automake，libtool/2.5.4 提供
        # libtoolize，经 VirtualBuildEnv 注入 conanbuild PATH。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # VirtualBuildEnv 把 tool_requires(automake/libtool) 的 bin 目录与
        # ACLOCAL_PATH 等注入 conanbuild 环境（先例：abiword-plugin-*）。
        # 必须在 AutotoolsToolchain.generate() 之前，两份环境文件按序合并。
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-zlib=no")
        tc.configure_args.append("--with-libxml2=no")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        os.umask(0)
        # 注意：不在此处 apply_conandata_patches——conandata 里唯一的补丁是
        # 0001-config.guess-ohos.patch，其目标是 autoreconf --install 重新
        # 注入的 config.guess；autoreconf 前应用会被 automake/1.18 的
        # share/config.guess 覆盖（E604 同款时序陷阱）。补丁在下面
        # autoreconf 完成后应用并验证。
        # GitHub tag 归档只带 configure.ac（autogen.sh 上游引导入口），需在
        # source 目录生成 configure（仓库先例：abiword/adcli/afuse 系）。
        # 不能直接跑 autogen.sh：它逐个探测工具且 `set -e`，环境差异即失败。
        self.run("mkdir -p m4", cwd=self.source_folder)
        # E443/PR#8033：autoreconf 在 PATH（CI worker/本机皆有），但兄弟工具
        # aclocal/automake/libtoolize 由 tool_requires(automake/libtool) 经
        # VirtualBuildEnv 注入的 conanbuild PATH 提供（确定性，不依赖本机
        # 安装布局）。解析优先用 VirtualBuildEnv 合并后的 effective PATH，
        # autoreconf realpath 有界搜索仅作 fallback；缺一即 fail closed，
        # 绝不静默跳过 autoreconf，不写全局 os.environ。
        build_env = VirtualBuildEnv(self).vars()
        with build_env.apply():
            resolved, sources = self._resolve_autotools_tools()
            self.output.info("autotools closure: " + ", ".join(
                "{}={} [{}]".format(t, resolved[t], sources[t])
                for t in _AUTOTOOLS_TOOLS))
            # tool_requires 注入的工具目录前置到局部 PATH（若 effective PATH
            # 已解析到工具，此前置只是幂等加固；fallback 场景才真正起效）。
            env = Environment()
            for d in dict.fromkeys(os.path.dirname(resolved[t])
                                   for t in _AUTOTOOLS_TOOLS):
                env.prepend_path("PATH", d)
            # autoconf 手册：autoreconf 遵守 ACLOCAL/AUTOMAKE/LIBTOOLIZE 环境
            # 变量。显式指向解析到的二进制，即使 PATH 混入宿主同名包装器
            # （E049：ohpcd wrapper 不可靠）也不会被误用。
            env.define_path("ACLOCAL", resolved["aclocal"])
            env.define_path("AUTOMAKE", resolved["automake"])
            env.define_path("LIBTOOLIZE", resolved["libtoolize"])
            with env.vars(self).apply():
                # env=None：直接继承当前作用域已 apply 的 os.environ
                # （VirtualBuildEnv 合并 PATH + 局部 Environment 的 PATH 与
                # ACLOCAL/AUTOMAKE/LIBTOOLIZE）。若传 env="conanbuild" 会
                # 在外层再 source conanbuildenv 脚本，其中 tool 包自带的
                # 同名变量会覆盖上面解析好的确定性路径。
                self.run("autoreconf --force --install -I m4",
                         cwd=self.source_folder, env=None)
                # E114：config.status 用 umask 077 建临时目录，HMDFS 上变成不可写
                # 的 drwx--S---；放宽为 000。config.guess 的 dummy.c 编译探测
                # 同样受 umask 077 限制（无法创建 dummy.c → cannot guess
                # build type），两个文件一并处理。
                self.run("sed -i 's/umask 077/umask 000/g' configure config.guess",
                         cwd=self.source_folder)
                # fail closed：替换后任一文件仍残留 umask 077（automake 升级
                # 换模板等）就直接中断并打印残留行，不带病走到 HMDFS 权限错误。
                self.run("! grep -n 'umask 077' configure config.guess",
                         cwd=self.source_folder)
                # ── OHOS config.guess 修复（E007/E019，非 E604）──
                # automake/1.18 经 autoreconf --install 注入的 config.guess
                # 版本为 2024-07-27，不含 HarmonyOS 识别分支：本机 uname 为
                # UNAME_SYSTEM=HarmonyOS（HongMeng Kernel），任何既有 case
                # 均不命中，configure 报 "cannot guess build type" 中断。
                # 补丁（conandata patches/0001-config.guess-ohos.patch）加两处：
                # LIBC 探测块 __OHOS__ 分支 + 主 case 的 *:HarmonyOS:*:*
                # 分支（GUESS=$UNAME_MACHINE-unknown-linux-ohos）。
                # 必须在 autoreconf 之后应用（否则被覆盖）；config.sub
                # （automake/1.18 自带 2024-08-04 版）已原生接受
                # aarch64-unknown-linux-ohos，无需补丁。conan.tools.files.patch
                # 底层用 patch_ng，应用失败直接抛 ConanException（fail closed）。
                config_guess = os.path.join(self.source_folder, "config.guess")
                config_sub = os.path.join(self.source_folder, "config.sub")
                if not os.path.isfile(config_guess):
                    raise ConanInvalidConfiguration(
                        "libmobi/0.12: autoreconf did not install "
                        "config.guess into the source folder (expected "
                        "{})".format(config_guess))
                if not os.path.isfile(config_sub):
                    raise ConanInvalidConfiguration(
                        "libmobi/0.12: autoreconf did not install "
                        "config.sub into the source folder (expected "
                        "{})".format(config_sub))
                # 幂等守卫：OHOS 适配版 autotools（如宿主 automake 1.16.5 的
                # share/config.guess，CI profile 前置 PATH 时生效）注入的
                # config.guess 已内置 HarmonyOS 分支，补丁上下文必然失配
                # （*:NetBSD 前已是 *:HarmonyOS）——此时跳过补丁，直接进入
                # 下方统一强制验证（验证不通过仍然 fail closed）。vanilla
                # automake（conan automake/1.18 的 2024-07-27 版，远端 CI
                # 实际路径）缺分支，走严格补丁。两个Marker 要求同时存在，
                # 半修补状态仍会尝试补丁并在上下文失配时大声失败。
                with open(config_guess, "r", encoding="utf-8",
                          errors="replace") as f:
                    pre_patch_text = f.read()
                already_ohos = ("*:HarmonyOS:*:*)" in pre_patch_text
                                and "__OHOS__" in pre_patch_text)
                if already_ohos:
                    self.output.info(
                        "config.guess already HarmonyOS-aware "
                        "(OHOS-adapted autotools); skipping "
                        "0001-config.guess-ohos.patch")
                else:
                    for patch_entry in self.conan_data.get("patches", {}).get(
                            str(self.version), []):
                        # patch_file 相对 export_sources_folder（conan 2.29
                        # 语义），应用目标 root 为 source_folder（autoreconf
                        # 刚重新生成 config.guess 的地方）；fuzz=False：上下文
                        # 必须严格匹配，automake 换代时宁可失败也不静默错位。
                        patch(self, patch_file=patch_entry["patch_file"],
                              strip=1, fuzz=False)
                # ── 补丁结果强制验证（configure 前，任一失败即终止）──
                # (1) config.guess 输出标准 OHOS 三元组（也确认无 umask 残留
                #     导致的 dummy.c Permission denied）。subprocess 直接捕获
                #     输出做严格断言（ConanFile.run 不返回 stdout）。
                guess_out = subprocess.run(
                    ["sh", "config.guess"], cwd=self.source_folder,
                    capture_output=True, text=True)
                if guess_out.returncode != 0:
                    raise ConanInvalidConfiguration(
                        "libmobi/0.12 config.guess exited {} (stderr: {!r}) "
                        "— umask/patch verification failed".format(
                            guess_out.returncode,
                            guess_out.stderr.strip()[:200]))
                guess_triplet = guess_out.stdout.strip()
                if guess_triplet != "aarch64-unknown-linux-ohos":
                    raise ConanInvalidConfiguration(
                        "libmobi/0.12 config.guess: expected "
                        "'aarch64-unknown-linux-ohos', got {!r}".format(
                            guess_triplet))
                # (2) config.sub 接受该三元组（automake/1.18 版已内置 ohos）
                sub_out = subprocess.run(
                    ["sh", "config.sub", "aarch64-unknown-linux-ohos"],
                    cwd=self.source_folder, capture_output=True, text=True)
                if sub_out.returncode != 0:
                    raise ConanInvalidConfiguration(
                        "libmobi/0.12 config.sub rejected "
                        "aarch64-unknown-linux-ohos (exit {}, stderr: "
                        "{!r})".format(sub_out.returncode,
                                       sub_out.stderr.strip()[:200]))
                sub_triplet = sub_out.stdout.strip()
                if sub_triplet != "aarch64-unknown-linux-ohos":
                    raise ConanInvalidConfiguration(
                        "libmobi/0.12 config.sub: expected "
                        "'aarch64-unknown-linux-ohos', got {!r}".format(
                            sub_triplet))
                # (3) 补丁分支确实存在（防止 conan patch 静默改错目标）
                with open(config_guess, "r", encoding="utf-8",
                          errors="replace") as f:
                    guess_text = f.read()
                if ("*:HarmonyOS:*:*)" not in guess_text
                        or "__OHOS__" not in guess_text):
                    raise ConanInvalidConfiguration(
                        "libmobi/0.12 config.guess: OHOS patch branches "
                        "(*:HarmonyOS:*:* / __OHOS__) missing after patch")
                # (4) umask 残留最终防线（与上面 grep 断言互补，防止补丁过程
                #     重新引入 077 权限模式的模板行）
                if "umask 077" in guess_text:
                    raise ConanInvalidConfiguration(
                        "libmobi/0.12 config.guess: umask 077 residue "
                        "present after OHOS patch")
                self.output.info(
                    "config.guess → {} (HarmonyOS branch present, "
                    "config.sub accepts it)".format(guess_triplet))
                autotools = Autotools(self)
                autotools.configure()
                # E074：HMDFS jobserver fifo EPERM → 单线程 make
                autotools.make(args=["-j1"])
                # E570：上游 make check 自动化（不可手工 sed）。
                # conan VPATH 构建下 configure 生成的 tests/test.sh 有两处
                # 在本机环境失效，均在构建目录生成版上做严格单处替换，
                # 不触碰上游源码模板 tests/test.sh.in，也不改动任何断言：
                # (1) @MD5PROG@ 展开为 "md5sum -t"（GNU md5sum 的 -t/--text
                #     开关），本机/设备为 toybox md5sum，不支持 -t，不修则
                #     12 个用例全部 die $skip；
                # (2) 模板假设 in-tree 构建（srcdir 为相对路径），diff 第二
                #     参数写死 "..${separator}..${separator}" 前缀；VPATH 下
                #     md5file_markup 为绝对路径，前缀拼接得到
                #     ../..//storage/... 畸形路径，diff 必然 Can't stat。
                test_sh = os.path.join(self.build_folder, "tests", "test.sh")
                with open(test_sh, "r", encoding="utf-8") as f:
                    content = f.read()
                patches = [
                    ('md5prog="md5sum -t"',
                     'md5prog="md5sum"'),
                    ('diff -w "..${separator}${testfile_md5}.md5" '
                     '"..${separator}..${separator}${md5file_markup}"',
                     'diff -w "..${separator}${testfile_md5}.md5" '
                     '"${md5file_markup}"'),
                ]
                for marker, replacement in patches:
                    count = content.count(marker)
                    if count != 1:
                        # fail closed：模板演替（automake/configure 换代）导致
                        # 匹配数漂移时中断，绝不带病静默跑测试
                        raise ConanInvalidConfiguration(
                            "libmobi/0.12 upstream test.sh patch: expected "
                            "exactly 1 occurrence of {!r}, found {} in "
                            "{}".format(marker, count, test_sh))
                    content = content.replace(marker, replacement)
                with open(test_sh, "w", encoding="utf-8") as f:
                    f.write(content)
                # make check：上游 tests/ 全量驱动（12 用例），结果断言见下
                autotools.make(target="check", args=["-j1"])
                # 解析 test-suite.log：必须 11 PASS + 1 XFAIL + 0 FAIL/ERROR/SKIP
                # automake 摘要行的键唯一（# TOTAL/# PASS/# SKIP/# XFAIL/
                # # FAIL/# XPASS/# ERROR），比逐用例行更稳，不受用例正文
                # 中的 PASS/FAIL 字样干扰。
                suite_log = os.path.join(self.build_folder, "tests",
                                         "test-suite.log")
                with open(suite_log, "r", encoding="utf-8", errors="replace") as f:
                    log_text = f.read()
                summary = {}
                for line in log_text.splitlines():
                    if line.startswith("# "):
                        key, _, val = line[2:].partition(":")
                        if key in ("TOTAL", "PASS", "SKIP", "XFAIL", "FAIL",
                                   "XPASS", "ERROR"):
                            summary[key] = summary.get(key, 0) + int(val.strip())
                total = summary.get("TOTAL", 0)
                passes = summary.get("PASS", 0)
                skips = summary.get("SKIP", 0)
                xfails = summary.get("XFAIL", 0)
                fails = summary.get("FAIL", 0)
                xpasses = summary.get("XPASS", 0)
                errors = summary.get("ERROR", 0)
                if not (total == 12 and passes == 11 and xfails == 1
                        and fails == 0 and errors == 0 and skips == 0
                        and xpasses == 0):
                    raise ConanInvalidConfiguration(
                        "libmobi/0.12 upstream make check: expected 11 PASS + "
                        "1 XFAIL + 0 FAIL/ERROR/SKIP/XPASS, got P={} X={} "
                        "F={} E={} S={} XP={} (total {})".format(
                            passes, xfails, fails, errors, skips, xpasses,
                            total))

    def package(self):
        # install 与 build 保持同一构建环境作用域（VirtualBuildEnv），不写
        # 全局 os.environ；签名在作用域外按基础 PATH 发现并 fail closed。
        build_env = VirtualBuildEnv(self).vars()
        with build_env.apply():
            autotools = Autotools(self)
            autotools.install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS PC XPM: dlopen-able .so and exec-able binaries in bin/ both
        # need a valid code signature, otherwise Permission denied /
        # Operation not permitted at runtime.
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        # Discover signing tools from PATH and fail closed when unavailable.
        objcopy = shutil.which("llvm-objcopy")
        signer = shutil.which("binary-sign-tool")
        if not objcopy or not signer or not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanInvalidConfiguration("llvm-objcopy / binary-sign-tool not found for OHOS code signing")
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}"'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    @staticmethod
    def _autotools_tool_dirs(entry, real):
        # E443：从 autoreconf 入口目录与 realpath 目录各自向上最多
        # _AUTOTOOLS_SEARCH_DEPTH 层派生候选根目录；每个根只探测其 bin、
        # libexec 及一层子目录下的 bin/libexec。不硬编码任何前缀或版本。
        roots = []
        for start in (os.path.dirname(entry), os.path.dirname(real)):
            d = start
            for _ in range(_AUTOTOOLS_SEARCH_DEPTH + 1):
                if d not in roots:
                    roots.append(d)
                parent = os.path.dirname(d)
                if parent == d:
                    break
                d = parent
        tool_dirs = []
        # autoreconf 入口目录与 realpath 目录本身即首选候选（同级兄弟工具
        # 就装在那里），不依赖其恰好名为 bin/libexec。
        for d in (os.path.dirname(entry), os.path.dirname(real)):
            if d not in tool_dirs:
                tool_dirs.append(d)
        for root in roots:
            probes = [os.path.join(root, s) for s in ("bin", "libexec")]
            try:
                probes += [os.path.join(root, n, s) for n in os.listdir(root)
                           for s in ("bin", "libexec")]
            except OSError:
                pass
            for p in probes:
                if p not in tool_dirs and os.path.isdir(p):
                    tool_dirs.append(p)
        return tool_dirs

    def _resolve_autotools_tools(self):
        # E443：解析宿主 Autotools 工具闭包。优先用 VirtualBuildEnv 合并后的
        # effective PATH（tool_requires 的 automake/libtool 包 bin 目录已前置），
        # aclocal/automake/libtoolize 应确定性解析到 Conan 包目录；仅当
        # effective PATH 找不到时，才退回 autoreconf realpath 的有界向上搜索
        # （双起点、最多 _AUTOTOOLS_SEARCH_DEPTH 层，不硬编码任何前缀/版本）。
        # 每个工具都记录来源：effective-path 或 realpath-fallback。
        effective_path = os.environ.get("PATH", "")

        def _find_on_path(tool):
            # 调用方已 apply VirtualBuildEnv，PATH 含 tool_requires 注入的
            # 包 bin 目录（前置）；逐目录验证可执行普通文件。
            for d in effective_path.split(os.pathsep):
                if not d:
                    continue
                p = os.path.normpath(os.path.join(d, tool))
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    return p
            return None

        entry = _find_on_path("autoreconf")
        if not entry:
            # 基础 PATH 也找不到 autoreconf（构建机未装）→ fail closed
            entry = shutil.which("autoreconf")
            if not entry:
                raise ConanInvalidConfiguration(
                    "libmobi/0.12 needs host autoreconf to bootstrap the source "
                    "archive (no pre-generated configure), but autoreconf is not "
                    "on PATH")
        entry = os.path.abspath(entry)
        real = os.path.realpath(entry)
        tool_dirs = LibmobiConan._autotools_tool_dirs(entry, real)
        resolved, sources = {}, {}
        for tool in _AUTOTOOLS_TOOLS:
            p = _find_on_path(tool)
            if p:
                resolved[tool], sources[tool] = os.path.abspath(p), "effective-path"
                continue
            # fallback：仅在 autoreconf 派生的候选目录中找（不扫全局 PATH）
            for d in tool_dirs:
                p = os.path.join(d, tool)
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    resolved[tool], sources[tool] = p, "realpath-fallback"
                    break
        missing = [t for t in _AUTOTOOLS_TOOLS if t not in resolved]
        if missing:
            resolved_txt = "; ".join("{}={} [{}]".format(
                t, resolved[t], sources[t])
                for t in _AUTOTOOLS_TOOLS if t in resolved) or "(none)"
            raise ConanInvalidConfiguration(
                "libmobi/0.12 autotools bootstrap closure incomplete; missing: {}\n"
                "  autoreconf entry: {}\n"
                "  autoreconf realpath: {}\n"
                "  resolved: {}\n"
                "  candidate tool dirs: {}".format(
                    ", ".join(missing), entry, real, resolved_txt,
                    "; ".join(tool_dirs) or "(none)"))
        return resolved, sources

    def package_info(self):
        self.cpp_info.libs = ["mobi"]
        self.cpp_info.set_property("cmake_file_name", "libmobi")
        self.cpp_info.set_property("cmake_target_name", "libmobi::libmobi")
        self.cpp_info.set_property("pkg_config_name", "libmobi")
