#!/usr/bin/env python3
"""Conan recipe — libapparmor 5.0.0 (Autotools).

与 psfex/scamp/skymaker 等既有 autotools 库一致：GitLab 官方仓库（v5.0.0 tag）
不含预生成 configure，需 autoreconf 自举；autotools 工具链经 conan tool_requires
（automake/1.18 + libtool/2.5.4）从 ohpcd 提供，不依赖宿主环境——CI worker
（uid 100）对 usr/local/bin 的 aclocal/automake 无读权限（"inaccessible"），
tool_requires 方案注入自己的工具链从而规避。

source() 用 git clone（git 自带独立 ssl，规避 CI Python 无 SSL 模块时 conan
get() 走 urllib 下载 https tarball 失败的 E372 场景）。源码缺 m4/
ax_check_compile_flag.m4 与 pkg.m4（autoconf-archive / pkg-config 宏），
build() 先动态写入再 autoreconf。
"""
import os
import re as _re
import glob as _glob

from conan import ConanFile
from conan.tools.files import patch, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.scm import Git


class LibapparmorConan(ConanFile):
    name = "libapparmor"
    version = "5.0.0"
    description = "AppArmor userspace library (libapparmor) — security policy interface"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.com/apparmor/apparmor"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # GitHub/GitLab archive 无预生成 configure，需 autoreconf 自举（同 psfex/scamp）
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # CI worker 的 Python 无 SSL 模块且无 curl（E372），conan get() 走 urllib
        # 无法下载 https tarball；改用 git clone（git 自带独立 ssl）。
        # source_folder 根已有 exports_sources 的 patches/（非空），clone 落到
        # apparmor/ 子目录，build()/package() 路径相应指向该子目录。
        git = Git(self)
        git.clone(url="https://gitlab.com/apparmor/apparmor.git",
                  target="apparmor",
                  args=["--depth", "1", "--branch", "v5.0.0"])

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: system-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def _libdir(self):
        return os.path.join(self.source_folder, "apparmor", "libraries", "libapparmor")

    def _write_m4_macros(self, libdir):
        """写入缺失的 autoconf m4 宏（autoconf-archive / pkg-config 宏，源码树未带）：
        - m4/ax_check_compile_flag.m4（AX_CHECK_COMPILE_FLAG）
        - m4/pkg.m4（PKG_PROG_PKG_CONFIG 精简宏，OHOS 无 pkg-config 的 pkg.m4）"""
        m4dir = os.path.join(libdir, "m4")
        os.makedirs(m4dir, exist_ok=True)
        ax = os.path.join(m4dir, "ax_check_compile_flag.m4")
        if not os.path.isfile(ax):
            with open(ax, "w") as f:
                f.write('''# ===========================================================================
#   https://www.gnu.org/software/autoconf-archive/ax_check_compile_flag.html
# ===========================================================================
AC_DEFUN([AX_CHECK_COMPILE_FLAG],
[AC_PREREQ(2.64)dnl for _AC_LANG_PREFIX and AS_VAR_IF
AS_VAR_PUSHDEF([CACHEVAR],[ax_cv_check_[]_AC_LANG_ABBREV[]flags_$4_$1])dnl
AC_CACHE_CHECK([whether _AC_LANG compiler accepts $1], CACHEVAR, [
  ax_check_save_flags=$[]_AC_LANG_PREFIX[]FLAGS
  _AC_LANG_PREFIX[]FLAGS="$[]_AC_LANG_PREFIX[]FLAGS $4 $1"
  AC_COMPILE_IFELSE([m4_default([$5],[AC_LANG_PROGRAM()])],
    [AS_VAR_SET(CACHEVAR,[yes])],
    [AS_VAR_SET(CACHEVAR,[no])])
  _AC_LANG_PREFIX[]FLAGS=$ax_check_save_flags])
AS_VAR_IF(CACHEVAR,yes,
  [m4_default([$2], :)],
  [m4_default([$3], :)])
AS_VAR_POPDEF([CACHEVAR])dnl
])dnl AX_CHECK_COMPILE_FLAG
''')
        pkg = os.path.join(m4dir, "pkg.m4")
        if not os.path.isfile(pkg):
            with open(pkg, "w") as f:
                f.write('''# pkg.m4 — 最小 PKG_PROG_PKG_CONFIG 宏（OHOS 环境无 pkg-config 的 pkg.m4）
AC_DEFUN([PKG_PROG_PKG_CONFIG],
[AC_ARG_VAR([PKG_CONFIG], [path to pkg-config utility])
if test -n "$PKG_CONFIG"; then
  AC_MSG_CHECKING([for pkg-config])
  AC_MSG_RESULT([$PKG_CONFIG])
else
  AC_PATH_TOOL([PKG_CONFIG], [pkg-config], [pkg-config])
  if test -n "$PKG_CONFIG"; then
    AC_MSG_CHECKING([for pkg-config])
    AC_MSG_RESULT([$PKG_CONFIG])
  else
    AC_MSG_WARN([pkg-config not found])
  fi
fi])dnl PKG_PROG_PKG_CONFIG
''')

    def _patch_ohos_autotools(self, libdir):
        """对 autoreconf 生成的 config.guess/config.sub 内联补 OHOS 识别
        （同 psfex/scamp 先例）。"""
        # config.guess/config.sub 实际所在：autoreconf --add-missing 后可能落在
        # 顶层或 AC_CONFIG_AUX_DIR 指定目录，按文件存在性搜索（同 psfex）。
        cg = cs = None
        for cand in (libdir,
                     os.path.join(libdir, "autoconf"),
                     os.path.join(libdir, "config")):
            cg_c = os.path.join(cand, "config.guess")
            cs_c = os.path.join(cand, "config.sub")
            if cg is None and os.path.isfile(cg_c):
                cg = cg_c
            if cs is None and os.path.isfile(cs_c):
                cs = cs_c
            if cg and cs:
                break
        # --- config.guess ---
        if cg and os.path.isfile(cg):
            text = open(cg, encoding="utf-8", errors="ignore").read()
            changed = False
            if "__OHOS__" not in text:
                new = text.replace(
                    "#if defined(__ANDROID__)\n    LIBC=android",
                    "#if defined(__ANDROID__)\n    LIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos")
                changed = new != text
                text = new
            if "HarmonyOS" not in text:
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
                new = _re.sub(r"(^[ \t]+\*:NetBSD:\*:\*\)[ \t]*\n)", block + r"\1", text, flags=_re.M)
                changed = changed or new != text
                text = new
            if changed:
                open(cg, "w", encoding="utf-8").write(text)
                self.output.info("已修补 config.guess: 加入 HarmonyOS 识别")
        # --- config.sub ---
        if cs and os.path.isfile(cs):
            text = open(cs, encoding="utf-8", errors="ignore").read()
            changed = False
            if "ohos-linux" not in text:
                pat = _re.compile(
                    r"(?P<ind>^\s*)android-linux\)\n"
                    r"(?P<body>(?:\s*basic_machine=\$field1-unknown\n)?"
                    r"\s*basic_os=linux-android\n"
                    r"\s*;;\n)",
                    _re.M)
                m = pat.search(text)
                if m:
                    ind = m.group("ind")
                    new = (
                        m.group(0) +
                        ind + "ohos-linux)\n" +
                        ind + "basic_machine=$field1-unknown\n" +
                        ind + "basic_os=linux-ohos\n" +
                        ind + ";;\n")
                    text = text[:m.start()] + new + text[m.end():]
                    changed = True
            if "gnu* | android* | ohos*" not in text:
                new = text.replace("gnu* | android*", "gnu* | android* | ohos*")
                changed = changed or new != text
                text = new
            if "linux-ohos" not in text:
                new = text.replace("linux-uclibc* )", "linux-uclibc* | linux-ohos* )")
                new = new.replace("linux-uclibc*- )", "linux-uclibc*- | linux-ohos*- )")
                changed = changed or new != text
                text = new
            if changed:
                open(cs, "w", encoding="utf-8").write(text)
                self.output.info("已修补 config.sub: 加入 ohos triplet 支持")

    def build(self):
        # 源码在 apparmor/ 子目录，conandata 补丁路径（a/libraries/...）需以
        # apparmor/ 为 base_path 应用（apply_conandata_patches 在 source_folder
        # 根应用会路径不匹配）。
        patch(self, base_path=os.path.join(self.source_folder, "apparmor"),
              patch_file=os.path.join(self.source_folder, "patches",
                                      "0001-libraries-libapparmor-src-Makefile.am.patch"),
              strip=1)
        # conan automake/1.18 包需 PERL5LIB 指向包内 share/automake-1.18
        # 才能找到 Automake/Config.pm。conanbuildenv 生成的 PERL5LIB 是
        # "usr/local/share/automake-1.16:.../automake-1.18"（profile buildenv
        # 的 1.16 在前），conan automake 1.18 会加载 1.16 模块报
        # "version mismatch. This is Automake 1.16.5 ... comes from Automake
        # 1.18"。self.run 内部会重载 conanbuildenv 覆盖 os.environ，且
        # self.dependencies 取不到 tool_requires 包——改在命令内用 $AUTOMAKE
        # 环境变量（conanbuildenv 已 export，指向 conan 包 bin/automake）推算
        # 包内 share/automake-1.18，内联 PERL5LIB 前缀强制覆盖。
        libdir = self._libdir()
        # 源码缺 m4 宏（ax_check_compile_flag / pkg.m4），先写入再 autoreconf
        self._write_m4_macros(libdir)
        autotools = Autotools(self)
        if not os.path.isfile(os.path.join(libdir, "configure")):
            self.output.info("源码树无 configure（GitLab archive 常见），先 autoreconf 自举")
            # $AUTOMAKE = <pfx>/bin/automake → <pfx>/share/automake-1.18
            # -I m4：configure.ac 无 AC_CONFIG_MACRO_DIR，aclocal 默认不搜 m4/
            # 子目录，需显式指定才能纳入写入的 ax_check_compile_flag.m4/pkg.m4。
            self.run(f"cd {libdir} && "
                     f"AM_PFX=$(dirname $(dirname \"$AUTOMAKE\")) && "
                     f"PERL5LIB=\"$AM_PFX/share/automake-1.18\" autoreconf -fiv -I m4")
            self._patch_ohos_autotools(libdir)
        # E011: HMDFS/SELinux 下 config.status 用 umask 077 创建临时目录不可写，
        # 就地改 configure 脚本中 umask 077→000（liburcu/psfex 同款修复）
        for _cfg in _glob.glob(os.path.join(libdir, "**", "configure"), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 000"))
        self.run(f"cd {libdir} && ./configure --prefix=/ --enable-static --disable-shared")
        self.run(f"cd {libdir} && make -j1")

    def package(self):
        libdir = self._libdir()
        self.run(f"cd {libdir} && make install DESTDIR={self.package_folder}")

    def package_info(self):
        self.cpp_info.libs = ["apparmor"]
