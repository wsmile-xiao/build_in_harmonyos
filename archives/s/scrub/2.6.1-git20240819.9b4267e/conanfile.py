#!/usr/bin/env python3
"""Conan recipe — scrub 2.6.1-git20240819.9b4267e

Debian 快照形态（orig.tar.xz，无 configure/Makefile.in，需 autoreconf 自举），
对应上游 github.com/chaos/scrub master 9b4267e。纯 C 应用（libc+pthread），
无外部库依赖；显式 --without-libgcrypt 走自带 AES，保证上游测试集在设备/CI
一致为 23 项（test/Makefile.am: TESTS=t01..t22 + 无 gcrypt 时条件追加 t00）。

构建期自举链（OHOS 上 autoreconf 全链有 autoconf.m4f 加载冲突，按仓库 abiword
家族先例走直跑链；worker PATH 无 automake/libtool，故 tool_requires 拉入）：
    aclocal --force → 复制 ltmain.sh → autoconf → autoheader →
    automake --add-missing --copy --no-force
随后对生成的 config.guess/config.sub 打 OHOS 识别补丁（等价
scripts/patch-autotools-ohos.pl 的 5 处变换；CI 不设 OHC_SKILL_ROOT，故内嵌）。
"""
import os
import re
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout

# make check 允许的环境性失败白名单（白名单外出现失败直接 ConanException）。
# t13/t14：上游脚本 unset TMPDIR 强制走 ${TMPDIR:-/tmp}，真机 /tmp 只读（设备
# 边界 §一.1，t14 第 3 行显式 unset）；CI worker /tmp 可写时会自然 PASS
# （空失败集 ⊆ 白名单同样成立）。
KNOWN_ENV_FAILS = {"t13", "t14"}


class ScrubConan(ConanFile):
    name = "scrub"
    version = "2.6.1-git20240819.9b4267e"
    description = ("scrub — disk/media scrubbing utility: iteratively overwrites "
                   "files and raw devices with known patterns to hinder recovery")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/chaos/scrub"
    url = ""
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # git 快照 tarball 无 configure/Makefile.in；CI worker PATH 无 automake，
        # /data/service/hnp/bin 只有 autoconf 家族没有 automake/libtool —— 与
        # abiword-plugin-* 家族同一对策：tool_requires 从制品仓拉入（1.18/2.5.4
        # 已发布，conan download 实查）。tool_requires 按 build profile 解析，
        # conan create 需同时传 -pr:h 与 -pr:b。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 自举与构建都跑在 conanbuild 环境里（tool_requires 注入的
        # ACLOCAL/AUTOMAKE/LIBTOOLIZE/ACLOCAL_PATH 只对该环境生效）
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # 显式关闭可选依赖，杜绝「探测到什么用什么」导致的设备/CI 漂移：
        # libgcrypt 有则链之且测试集缩为 22 项（无 t00），无则自带 AES。
        # 固定走自带 AES ⇒ N=23 恒定。
        tc.configure_args.append("--without-libgcrypt")
        # libscrub 共享库上游默认不启（AC_ARG_ENABLE 默认 false），保持默认。
        # 不传 --build/--host（R1/E007：config.guess 补丁后原生识别 OHOS）。
        tc.generate()

    # ── autoreconf 直跑链（见模块 docstring）────────────────────────────
    def _bootstrap_autotools(self):
        src = self.source_folder
        # configure.ac 已声明 AC_CONFIG_MACRO_DIR([config])，tarball 自带的
        # libgcrypt.m4/x_ac_*.m4/ac_pkgconfig.m4 由 aclocal 自动扫描
        self.run('"${ACLOCAL:-aclocal}" --force', cwd=src, env="conanbuild",
                 ignore_errors=True)  # aclocal 的宏重复/过时 warning 非硬错
        # automake 之前必须先有 aux 目录下的 ltmain.sh（本包
        # AC_CONFIG_AUX_DIR([config]) ⇒ 落 config/ltmain.sh；缺它 automake 报
        # "required file 'config/ltmain.sh' not found" 且 rc=1，实测首跑）。
        # ltmain.sh 在 libtool 包 share/libtool/build-aux/ 下，经 $LIBTOOLIZE
        # 定位（conanbuild 环境变量，Python 进程 os.environ 取不到，必须 shell 展开）。
        ltmain = os.path.join(src, "config", "ltmain.sh")
        if not os.path.exists(ltmain):
            self.run(
                'lt="$LIBTOOLIZE"; '
                'if [ -n "$lt" ] && [ -f "$lt" ]; then '
                '  srcdir="$(cd "$(dirname "$(dirname "$lt")")" && pwd)"; '
                '  src="$srcdir/share/libtool/build-aux/ltmain.sh"; '
                '  [ -f "$src" ] && cp "$src" config/ltmain.sh; '
                'fi',
                cwd=src, env="conanbuild", ignore_errors=True)
        if not os.path.exists(ltmain):
            try:
                _lt_pkg = self.dependencies["libtool"].package_folder
                _cand = os.path.join(_lt_pkg, "share", "libtool", "build-aux", "ltmain.sh")
                if _lt_pkg and os.path.exists(_cand):
                    shutil.copy(_cand, ltmain)
            except Exception:
                pass
        if not os.path.exists(ltmain):
            raise ConanException("config/ltmain.sh not found (libtool tool_requires broken?)")
        self.run('autoconf -o configure configure.ac', cwd=src, env="conanbuild")
        if not os.path.exists(os.path.join(src, "configure")):
            raise ConanException("autoconf failed to generate configure")
        self.run('autoheader', cwd=src, env="conanbuild")
        if not os.path.exists(os.path.join(src, "config", "config.h.in")):
            raise ConanException("autoheader did not produce config/config.h.in")
        # --add-missing 补 install-sh/missing/depcomp/compile/config.guess/config.sub
        self.run('"${AUTOMAKE:-automake}" --add-missing --copy --no-force',
                 cwd=src, env="conanbuild")
        for _aux in ("config.guess", "config.sub"):
            if not os.path.exists(os.path.join(src, "config", _aux)):
                raise ConanException(f"automake --add-missing did not install config/{_aux}")

    # ── config.guess/config.sub 的 OHOS 识别（E007）─────────────────────
    # 与 scripts/patch-autotools-ohos.pl 等价；CI 侧无 OHC_SKILL_ROOT，
    # 因此内嵌于配方（仅改 autoreconf 生成物，不进 patches/，不引平台宏）。
    # 设备实证（2026-09-22）：uname -s == "HarmonyOS"，未打补丁的
    # config.guess 直接 "unable to guess system type"（rc=1）⇒ *:HarmonyOS:*
    # case 块是必需项，命中后原生返回 aarch64-unknown-linux-ohos。
    # config.sub：automake 1.18/1.19 自带版本已原生接受 linux-ohos 三元
    # （实测 rc=0），故 config.sub 变换为带锚点才打的保险，验收改用功能
    # oracle：config.sub 必须成功归一化 aarch64-unknown-linux-ohos。
    def _patch_ohos_config_files(self, src):
        cg = os.path.join(src, "config", "config.guess")
        cs = os.path.join(src, "config", "config.sub")
        with open(cg, encoding="utf-8", errors="ignore") as f:
            t = f.read()
        if "__OHOS__" not in t:
            t, _ = re.subn(
                r"(^\s*#\s*if\s+defined\(__ANDROID__\)\s*\n\s*LIBC=android)",
                r"\1\n#elif defined(__OHOS__)\n    LIBC=ohos",
                t, count=1, flags=re.M)
        if "HarmonyOS" not in t:
            block = (
                "    *:HarmonyOS:*:*)\n"
                "\tcase \"$UNAME_MACHINE\" in\n"
                "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                "\t    i?86)         MACHINE=i686 ;;\n"
                "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                "\tesac\n"
                "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                "\t;;\n\n")
            t, n = re.subn(r"(^[ \t]+\*:NetBSD:\*:\*\)[ \t]*\n)",
                           block + r"\1", t, count=1, flags=re.M)
            if not n:
                raise ConanException(
                    "config.guess: NetBSD insertion anchor not found; "
                    "HarmonyOS uname would leave config.guess unable to guess")
        with open(cg, "w", encoding="utf-8") as f:
            f.write(t)
        if "__OHOS__" not in t or "HarmonyOS" not in t:
            raise ConanException("config.guess: OHOS markers missing after patch")

        with open(cs, encoding="utf-8", errors="ignore") as f:
            s = f.read()
        if "ohos-linux" not in s:
            s, _ = re.subn(
                r"^(\s*android-linux\)\s*\n)"
                r"((\s*)basic_machine=\$field1-unknown\s*\n)"
                r"((\s*)basic_os=linux-android\s*\n)"
                r"(\s*;;\s*\n)",
                r"\1\2\4\6"
                r"\tohos-linux)\n"
                r"\3basic_machine=$field1-unknown\n"
                r"\5basic_os=linux-ohos\n"
                r"\6",
                s, count=1, flags=re.M)
        with open(cs, "w", encoding="utf-8") as f:
            f.write(s)
        # 功能 oracle：config.guess 将产出 aarch64-unknown-linux-ohos，
        # config.sub 必须能归一化（automake 1.18/1.19 自带版本原生支持）
        self.run('sh config/config.sub aarch64-unknown-linux-ohos',
                 cwd=src, env="conanbuild")


    # ── E114：HMDFS 上 config.status 的 AS_TMPDIR 子进程写新目录被拦 ────
    def _patch_configure_ac_tmp(self, src):
        fixed_tmp = os.path.join(tempfile.gettempdir(), "scrub-ac-tmp")
        os.makedirs(fixed_tmp, exist_ok=True)
        os.environ["TMPDIR"] = fixed_tmp
        cfg_path = os.path.join(src, "configure")
        with open(cfg_path, encoding="utf-8") as f:
            cfg = f.read()
        if "ac_tmp=$tmp" not in cfg:
            raise ConanException(
                "E114: ac_tmp=$tmp pattern not found in configure; "
                "autoconf may have changed the template")
        cfg = cfg.replace("ac_tmp=$tmp", f"ac_tmp={fixed_tmp}")
        old_trap = '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status'
        if old_trap in cfg:  # 退出 trap 不删预建目录（否则后续轮次找不到）
            cfg = cfg.replace(old_trap, "exit $exit_status")
        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write(cfg)
        os.chmod(cfg_path, 0o755)

    # ── out-of-tree 构建时搬运测试夹具 ──────────────────────────────────
    # 上游按 in-tree/RPM buildfarm 惯例写死相对路径（`diff t00.exp t00.out`、
    # `./aestest`）；automake 并行 driver 在 build 目录跑用例，tNN 脚本能从
    # srcdir 找到，但脚本内部的 .exp 期望文件必须就在 cwd。把用例脚本与
    # .exp 复制进 build/test/ 后，driver 优先用 build 目录里的同名用例。
    def _stage_check_fixtures(self):
        src_t = os.path.join(self.source_folder, "test")
        bld_t = os.path.join(self.build_folder, "test")
        if os.path.abspath(src_t) == os.path.abspath(bld_t):
            return
        if not os.path.isdir(bld_t):
            raise ConanException("build test dir missing: " + bld_t)
        n = 0
        for name in os.listdir(src_t):
            if re.fullmatch(r"t\d{2}", name) or name.endswith(".exp"):
                shutil.copy2(os.path.join(src_t, name), os.path.join(bld_t, name))
                n += 1
        self.output.info(f"  [ok] staged {n} upstream test fixtures into build/test/")

    # ── 上游测试（make check）：解析 automake 测试摘要并强制白名单 ──────
    def _run_make_check(self):
        check_tmp = os.path.join(self.build_folder, "check-tmp")
        os.makedirs(check_tmp, exist_ok=True)
        log = os.path.join(self.build_folder, "make-check.log")
        # 测试经 ${TMPDIR:-/tmp} 建工作文件，显式指到可写目录（t13 上游
        # unset TMPDIR 强制走 /tmp，属预期环境性失败，见 KNOWN_ENV_FAILS）
        self.run(
            f'TMPDIR="{check_tmp}" make check -j1 >"{log}" 2>&1; '
            f'echo "make check exit code: $?"',
            env="conanbuild")
        with open(log, encoding="utf-8", errors="replace") as f:
            out = f.read()

        def _num(label):
            m = re.search(rf"^# {label}:\s+(\d+)", out, re.M)
            return int(m.group(1)) if m else None

        total = _num("TOTAL")
        if total is None:
            raise ConanException("make check produced no Testsuite summary — "
                                 "see make-check.log")
        n_pass, n_fail, n_skip = _num("PASS"), _num("FAIL"), _num("SKIP")
        if total != 23:
            raise ConanException(
                f"upstream test count drift: expected 23 (t00..t22, no-gcrypt path), "
                f"got {total}")
        # 失败清单以 test-suite.log 的行首 FAIL:/ERROR: 为准。
        # out-of-tree 构建下该文件在 build_folder/test/（实测首跑确认，
        # source_folder/test/ 不存在会让 allowlist 空判放行——必须双路探测）
        bad = []
        suite_log = os.path.join(self.build_folder, "test", "test-suite.log")
        if not os.path.exists(suite_log):
            suite_log = os.path.join(self.source_folder, "test", "test-suite.log")
        if not os.path.exists(suite_log):
            raise ConanException("test-suite.log not found in build/source tree — "
                                 "cannot verify per-test results (fail-closed)")
        if os.path.exists(suite_log):
            with open(suite_log, encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = re.match(r"^(?:FAIL|ERROR): (t\d+)", line)
                    if m and m.group(1) not in KNOWN_ENV_FAILS:
                        bad.append(m.group(1))
        if bad:
            raise ConanException(
                f"make check failed outside the known environment allowlist "
                f"{sorted(KNOWN_ENV_FAILS)}: {sorted(bad)} — real regression, "
                "see test/test-suite.log")
        self.output.info(
            f"  [ok] upstream make check: TOTAL={total} PASS={n_pass} "
            f"SKIP={n_skip} FAIL={n_fail} "
            f"(expected env-limited: {sorted(KNOWN_ENV_FAILS)})")

    def build(self):
        # 1) conandata 补丁打在源码上（configure.ac / src/getsize.c）
        apply_conandata_patches(self)
        # 2) autoreconf 直跑链自举
        self._bootstrap_autotools()
        # 3) config.guess/sub OHOS 识别
        self._patch_ohos_config_files(self.source_folder)
        # 4) E114 ac_tmp 修复（打在生成的 configure 上）
        self._patch_configure_ac_tmp(self.source_folder)
        # 5) configure / make / 上游测试
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        self._stage_check_fixtures()
        self._run_make_check()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # application 包：确认 bin/scrub 真实落盘（防 install 静默半途）
        if not os.path.exists(os.path.join(self.package_folder, "bin", "scrub")):
            raise ConanException("package(): bin/scrub missing after install")
        # 未构建任何库，无 .la 清理项；dist_doc_DATA 落 share/doc/scrub/

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
