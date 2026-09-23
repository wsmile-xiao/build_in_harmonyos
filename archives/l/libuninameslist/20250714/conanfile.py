#!/usr/bin/env python3
"""Conan recipe — libuninameslist 20250714 (autotools)

OHOS 适配要点：
- GitHub tag archive 不带预生成 configure/aclocal.m4/Makefile.in，
  build() 必须跑 autoreconf 自举（CI 沙箱不可见 $HOME/.local 手工工具，
  automake/libtool 经 tool_requires 拉入，制品仓已发布 1.18/2.5.4）。
- config.guess/config.sub 用 skill 的 patch-autotools-ohos.pl 补丁识别
  HarmonyOS 平台（R15：禁止 --build/--host 绕过）。
- E490: autoreconf 生成的辅助脚本 +x 后才可执行。
- R26: 非系统同名库，静态/动态由 Conan options 控制。
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibuninameslistConan(ConanFile):
    name = "libuninameslist"
    version = "20250714"
    description = "A Library of Unicode names and annotation data (NamesList.txt)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/fontforge/libuninameslist"
    url = "https://github.com/fontforge/libuninameslist"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # GitHub tag archive 不带 configure，需要 autoreconf 自举。
        # CI 沙箱(USER=100)看不到 $HOME/.local 手工安装的 automake，
        # 制品仓已发布 automake/1.18 + libtool/2.5.4，作为 tool_requires 拉入。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # E490: 辅助脚本需可执行（HMDFS 不保留存档位）
        for f in ("configure", "config.guess", "config.sub", "install-sh", "missing"):
            p = os.path.join(self.source_folder, f)
            if os.path.exists(p):
                os.chmod(p, 0o755)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: 非系统同名库，静态/动态由 options 控制
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # 1) 自举生成 configure（tag archive 无预生成 configure）
        self._bootstrap_autotools()

        # 2) config.guess/config.sub 补 HarmonyOS 识别（R15）
        self._patch_config_for_ohos()

        # 3) E490: 自举（重）生成的辅助脚本必须 +x
        for f in ("configure", "config.guess", "config.sub", "install-sh", "missing", "depcomp", "test-driver", "ltmain.sh"):
            p = os.path.join(self.source_folder, f)
            if os.path.exists(p):
                os.chmod(p, 0o755)

        # 4) E112/E114/E118: HMDFS 上 config.status 的 mktemp -d "./confXXXXXX"
        #    临时目录不可写（远端 CI 实测 ./confXXXXXX/subs1.awk: Permission denied
        #    → config.status: could not setup config files machinery）。预建固定可写
        #    目录并把 configure/config.status 的 ac_tmp 指向它，同时移除删除该目录
        #    的 trap（HMDFS 上 chmod 700 不保留 0700 位，实测为 2771，写权限由
        #    固定目录 + 实际属主保证）。仅当 configure 确实含该机制时才替换。
        self._patch_configure_tmp_for_ohos()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _patch_configure_tmp_for_ohos(self):
        """E112/E114/E118: config.status 临时目录绕过 mktemp（OHOS 平台权限限制）。"""
        cfg = os.path.join(self.source_folder, "configure")
        if not os.path.exists(cfg):
            self.output.info("configure not found, skipping tmp patch")
            return
        cfg_txt = open(cfg, "r", encoding="utf-8", errors="replace").read()
        if "ac_tmp" not in cfg_txt:
            self.output.info("configure has no ac_tmp machinery, skipping tmp patch")
            return
        if "OHOS_FIXED_AC_TMP" in cfg_txt:
            self.output.info("configure already patched for OHOS fixed tmp")
            return

        # 预建固定可写临时目录（沙箱内每一构建目录独立，避免跨包污染）
        fixed = os.path.join(self.build_folder, "conf-tmp")
        os.makedirs(fixed, exist_ok=True)
        os.chmod(fixed, 0o700)
        st = os.stat(fixed)
        self.output.info(
            "  [ok] fixed tmp dir {} mode={:o} ({})".format(
                fixed, st.st_mode & 0o777, oct(st.st_mode & 0o777)))

        # TMPDIR/TMP/TEMP 指向固定目录（configure/config.status/编译器共用）
        os.environ["TMPDIR"] = fixed
        os.environ["TMP"] = fixed
        os.environ["TEMP"] = fixed

        # 1) mktemp 行不再执行（ac_tmp 已被固定）——避免生成不可写目录
        cfg_txt = cfg_txt.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
            'tmp="{}" &&'.format(fixed))
        # 2) ac_tmp 指向固定目录（configure 内嵌 config.status 模板同时生效）
        cfg_txt = cfg_txt.replace("ac_tmp=$tmp", "ac_tmp={}".format(fixed))
        # 3) 移除删除固定目录的 trap（保留退出码）
        cfg_txt = cfg_txt.replace(
            '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status',
            "exit $exit_status")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write(cfg_txt)
        os.chmod(cfg, 0o755)
        self.output.info("  [ok] patched configure: ac_tmp -> {} (bypass-mktemp, E112/E114/E118)".format(fixed))

    def _bootstrap_autotools(self):
        """Run autoreconf -i to generate configure from configure.ac."""
        elif_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(elif_path):
            self.output.info("configure exists, skipping bootstrap")
            return
        # tool_requires 注入 ACLOCAL/AUTOMAKE 环境变量（conanbuildenv），
        # 裸命令在 CI 干净 PATH 不可见，用子 shell 展开。
        self.run(
            "autoreconf -i",
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.output.info("[ok] autoreconf -i bootstrap done")

    def _patch_config_for_ohos(self):
        """Patch config.guess/config.sub for OHOS (R15).

        纯 Python 内联实现（等价 scripts/patch-autotools-ohos.pl），
        不依赖 conan 构建环境外的 perl 二进制。
        """
        base = self.source_folder
        cg = os.path.join(base, "config.guess")
        cs = os.path.join(base, "config.sub")
        if not os.path.exists(cg) or not os.path.exists(cs):
            self.output.info("config.guess/config.sub not found, skipping OHOS patch")
            return

        # ---- config.guess ----
        with open(cg, "r", encoding="utf-8") as f:
            gc = f.read()
        changed = 0

        # 1.1 LIBC=ohos after android detection
        if "__OHOS__" not in gc:
            import re as _re
            new_gc, n = _re.subn(
                r"(#\s*if\s+defined\(__ANDROID__\)\s*\n\s*LIBC=android)",
                r"\1\n#elif defined(__OHOS__)\n    LIBC=ohos",
                gc, count=1)
            if n > 0:
                gc = new_gc
                changed += 1
                self.output.info("  [ok] Added __OHOS__ LIBC detection")

        # 1.2 HarmonyOS system identification before NetBSD case
        if "HarmonyOS" not in gc:
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
            new_gc, n = _re.subn(
                r"(^[ \t]+\*:NetBSD:\*:\*\)[ \t]*\n)",
                block + r"\1", gc, count=1, flags=_re.M)
            if n > 0:
                gc = new_gc
                changed += 1
                self.output.info("  [ok] Added HarmonyOS system identification")
        if changed:
            with open(cg, "w", encoding="utf-8") as f:
                f.write(gc)

        # ---- config.sub ----
        with open(cs, "r", encoding="utf-8") as f:
            sc = f.read()
        s_changed = 0

        # 2.1 ohos-linux triplet after android-linux
        if "ohos-linux" not in sc:
            new_sc, n = _re.subn(
                r"(\s*android-linux\)\s*\n\s*basic_machine=\$field1-unknown\s*\n\s*basic_os=linux-android\s*\n\s*;;\s*\n)",
                lambda m: m.group(1)
                + m.group(1).splitlines()[0].replace("android-linux", "ohos-linux") + "\n"
                + re.sub(r"android-linux", "ohos-linux", m.group(1).replace("linux-android", "linux-ohos").split("\n", 1)[1]),
                sc, count=1)
            if n > 0:
                sc = new_sc
                s_changed += 1
                self.output.info("  [ok] Added ohos-linux triplet")

        # 2.2 ohos* in OS type list
        if "android* | ohos*" not in sc and "android\\* | ohos*" not in sc:
            new_sc, n = _re.subn(r"(gnu\*\s*\|\s*android\*)", r"\1 | ohos*", sc, count=1)
            if n > 0:
                sc = new_sc
                s_changed += 1
                self.output.info("  [ok] Added ohos* to OS list")

        # 2.3 linux-ohos in kernel-OS validation list
        # (config.sub: case $kernel-$os-$obj in ... linux-uclibc*- )
        if "linux-ohos" not in sc:
            new_sc, n = _re.subn(
                r"(linux-(?:uclibc|musl|gnu|newlib)\*[\)\s-]*)",
                r"\1 | linux-ohos*", sc, count=1)
            if n > 0:
                sc = new_sc
                s_changed += 1
                self.output.info("  [ok] Added linux-ohos to kernel list")
        if s_changed:
            with open(cs, "w", encoding="utf-8") as f:
                f.write(sc)
        self.output.info("OHOS patch done: cg={} sub={}".format(changed, s_changed))

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["uninameslist"]